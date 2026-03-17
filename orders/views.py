from collections import OrderedDict
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from marketplace.models import Product
from .models import Cart, CartItem, Order, OrderItem, StatusUpdate


def _is_customer(user):
    role = getattr(user, "role", None)
    return role in (None, "customer")


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user, status=Cart.STATUS_ACTIVE)
    return cart


def _group_cart_items_by_producer(items):
    """Group CartItems by their product's producer, computing per-producer subtotals."""
    grouped = OrderedDict()
    for item in items:
        producer = item.product.producer
        if producer.id not in grouped:
            grouped[producer.id] = {"producer": producer, "items": [], "subtotal": Decimal("0.00")}
        grouped[producer.id]["items"].append(item)
        grouped[producer.id]["subtotal"] += item.line_total
    return list(grouped.values())


def _group_order_items_by_producer(items):
    """Group OrderItems by their product's producer, computing per-producer subtotals."""
    grouped = OrderedDict()
    for item in items:
        producer = item.product.producer if item.product else None
        key = producer.id if producer else 0
        if key not in grouped:
            grouped[key] = {"producer": producer, "items": [], "subtotal": Decimal("0.00")}
        grouped[key]["items"].append(item)
        grouped[key]["subtotal"] += item.line_total
    return list(grouped.values())


@login_required
def cart_detail(request):
    cart = _get_cart(request.user)
    items = cart.items.select_related("product", "product__producer").all()
    grouped_items = _group_cart_items_by_producer(items)
    return render(request, "orders/cart.html", {"cart": cart, "items": items, "grouped_items": grouped_items})


@login_required
def add_to_cart(request, product_id):
    if request.method != "POST":
        return redirect("orders:cart")

    product = get_object_or_404(Product, id=product_id)
    cart = _get_cart(request.user)

    qty = request.POST.get("quantity", "1")
    try:
        qty = int(qty)
    except ValueError:
        qty = 1
    qty = max(1, qty)

    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    item.quantity = qty if created else item.quantity + qty
    item.save()

    from django.contrib import messages
    messages.success(request, f'Successfully added {qty}x {product.name} to your cart.')

    next_url = request.META.get('HTTP_REFERER', 'orders:cart')
    return redirect(next_url)


@login_required
def update_cart_item(request, item_id):
    if request.method != "POST":
        return redirect("orders:cart")

    cart = _get_cart(request.user)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)

    qty = request.POST.get("quantity", str(item.quantity))
    try:
        qty = int(qty)
    except ValueError:
        qty = item.quantity

    if qty <= 0:
        item.delete()
        return redirect("orders:cart")

    item.quantity = qty
    item.save()
    return redirect("orders:cart")


@login_required
def remove_cart_item(request, item_id):
    if request.method != "POST":
        return redirect("orders:cart")

    cart = _get_cart(request.user)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    item.delete()
    return redirect("orders:cart")


@login_required
def checkout(request):
    if not _is_customer(request.user):
        raise Http404

    cart = _get_cart(request.user)
    items = cart.items.select_related("product", "product__producer").all()

    if not items.exists():
        return redirect("orders:cart")

    grouped_items = _group_cart_items_by_producer(items)
    commission = (cart.total * Order.COMMISSION_RATE).quantize(Decimal("0.01"))
    grand_total = cart.total + commission

    if request.method == "GET":
        return render(request, "orders/checkout.html", {
            "cart": cart, "items": items, "grouped_items": grouped_items,
            "commission": commission, "grand_total": grand_total,
        })

    with transaction.atomic():
        product_ids = [i.product_id for i in items]
        products = {p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)}

        for i in items:
            p = products.get(i.product_id)
            if p is None:
                raise Http404
            if hasattr(p, "stock") and p.stock < i.quantity:
                return redirect("orders:cart")

        # Validate Delivery Date (Minimum 48 Hours / 2 days)
        raw_delivery_date = request.POST.get("delivery_date", "").strip()
        try:
            parsed_date = datetime.strptime(raw_delivery_date, "%Y-%m-%d").date()
            if parsed_date < date.today() + timedelta(days=2):
                from django.contrib import messages
                messages.error(request, "Delivery date must be at least 48 hours away.")
                return redirect("orders:checkout")
        except ValueError:
            from django.contrib import messages
            messages.error(request, "Invalid delivery date.")
            return redirect("orders:checkout")

        order = Order.objects.create(
            user=request.user,
            full_name=request.POST.get("full_name", "").strip(),
            email=request.POST.get("email", "").strip(),
            address_line1=request.POST.get("address_line1", "").strip(),
            address_line2=request.POST.get("address_line2", "").strip(),
            city=request.POST.get("city", "").strip(),
            postcode=request.POST.get("postcode", "").strip(),
            total=Decimal("0.00"),
            delivery_date=parsed_date,
        )

        total = Decimal("0.00")

        for i in items:
            p = products[i.product_id]
            unit_price = p.price
            line_total = unit_price * i.quantity

            OrderItem.objects.create(
                order=order,
                product=p,
                product_name=getattr(p, "name", str(p.id)),
                unit_price=unit_price,
                quantity=i.quantity,
                line_total=line_total,
            )

            if hasattr(p, "stock"):
                p.stock -= i.quantity
                p.save(update_fields=["stock"])

            total += line_total

        order.total = total
        commission_amount = (total * Order.COMMISSION_RATE).quantize(Decimal("0.01"))
        order.commission = commission_amount
        order.save(update_fields=["total", "commission"])

        cart.status = Cart.STATUS_CONVERTED
        cart.save(update_fields=["status"])
        cart.items.all().delete()

    return redirect("orders:order_detail", order_id=order.id)


@login_required
def order_list(request):
    if not _is_customer(request.user):
        raise Http404
    orders = request.user.orders.order_by("-created_at")
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    if not _is_customer(request.user):
        raise Http404
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.items.select_related("product", "product__producer").all()
    grouped_items = _group_order_items_by_producer(items)
    status_updates = order.status_updates.all()
    return render(request, "orders/order_detail.html", {
        "order": order, "items": items, "grouped_items": grouped_items, "status_updates": status_updates,
    })


def _is_producer(user):
    return getattr(user, "role", None) == "producer"


@login_required
def manage_orders(request):
    if not _is_producer(request.user):
        raise Http404
    # Show orders that contain items from this producer, sorted by upcoming delivery
    orders = Order.objects.filter(items__product__producer=request.user).distinct().order_by("delivery_date", "-created_at")
    return render(request, "orders/manage_orders.html", {"orders": orders})


@login_required
def manage_order_detail(request, order_id):
    if not _is_producer(request.user):
        raise Http404
    
    # Must contain at least one item from this producer
    try:
        order = Order.objects.filter(id=order_id, items__product__producer=request.user).distinct().get()
    except Order.DoesNotExist:
        raise Http404
    items = order.items.filter(product__producer=request.user)
    
    from marketplace.forms import OrderStatusForm
    if request.method == "POST":
        form = OrderStatusForm(request.POST, current_status=order.status)
        if form.is_valid():
            old_status = order.status
            new_status = form.cleaned_data["status"]
            note = form.cleaned_data.get("note", "")

            if new_status != old_status:
                order.status = new_status
                order.save(update_fields=["status"])

                StatusUpdate.objects.create(
                    order=order,
                    old_status=old_status,
                    new_status=new_status,
                    note=note,
                    changed_by=request.user,
                )

                from django.contrib import messages
                messages.success(request, f"Order status updated to {order.get_status_display()}.")

            return redirect("orders:manage_order_detail", order_id=order.id)
    else:
        form = OrderStatusForm(initial={"status": order.status}, current_status=order.status)

    status_updates = order.status_updates.all()

    return render(request, "orders/manage_order_detail.html", {
        "order": order,
        "items": items,
        "form": form,
        "status_updates": status_updates,
    })