import stripe
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from marketplace.models import Product
from .models import Cart, CartItem, Order, OrderItem


def _is_customer(user):
    role = getattr(user, "role", None)
    return role in (None, "customer")


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user, status=Cart.STATUS_ACTIVE)
    return cart


@login_required
def cart_detail(request):
    cart = _get_cart(request.user)
    items = cart.items.select_related("product").all()
    return render(request, "orders/cart.html", {"cart": cart, "items": items})


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

    return redirect("orders:cart")


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
    items = cart.items.select_related("product").all()

    if not items.exists():
        return redirect("orders:cart")

    if request.method == "GET":
        return render(request, "orders/checkout.html", {"cart": cart, "items": items})

    # Save delivery details to session before redirecting to Stripe
    request.session["checkout_details"] = {
        "full_name": request.POST.get("full_name", "").strip(),
        "email": request.POST.get("email", "").strip(),
        "address_line1": request.POST.get("address_line1", "").strip(),
        "address_line2": request.POST.get("address_line2", "").strip(),
        "city": request.POST.get("city", "").strip(),
        "postcode": request.POST.get("postcode", "").strip(),
    }

    stripe.api_key = settings.STRIPE_SECRET_KEY

    line_items = []
    for item in items:
        line_items.append({
            "price_data": {
                "currency": "gbp",
                "product_data": {"name": item.product.name},
                "unit_amount": int(item.product.price * 100),
            },
            "quantity": item.quantity,
        })

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url=request.build_absolute_uri("/orders/checkout/success/") + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri("/orders/checkout/cancel/"),
    )

    return redirect(session.url)


@login_required
def stripe_success(request):
    session_id = request.GET.get("session_id")
    if not session_id:
        return redirect("orders:cart")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.retrieve(session_id)

    if session.payment_status != "paid":
        return redirect("orders:cart")

    cart = _get_cart(request.user)
    items = cart.items.select_related("product").all()

    if not items.exists():
        return redirect("orders:cart")

    details = request.session.pop("checkout_details", {})

    with transaction.atomic():
        product_ids = [i.product_id for i in items]
        products = {p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)}

        for i in items:
            p = products.get(i.product_id)
            if p is None:
                raise Http404
            if hasattr(p, "stock") and p.stock < i.quantity:
                return redirect("orders:cart")

        order = Order.objects.create(
            user=request.user,
            full_name=details.get("full_name", ""),
            email=details.get("email", ""),
            address_line1=details.get("address_line1", ""),
            address_line2=details.get("address_line2", ""),
            city=details.get("city", ""),
            postcode=details.get("postcode", ""),
            total=Decimal("0.00"),
            status=Order.STATUS_PAID,
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
        order.save(update_fields=["total"])

        cart.status = Cart.STATUS_CONVERTED
        cart.save(update_fields=["status"])
        cart.items.all().delete()

    return redirect("orders:order_detail", order_id=order.id)


@login_required
def stripe_cancel(request):
    return redirect("orders:checkout")


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
    items = order.items.all()
    return render(request, "orders/order_detail.html", {"order": order, "items": items})


def _is_producer(user):
    return getattr(user, "role", None) == "producer"


@login_required
def manage_orders(request):
    if not _is_producer(request.user):
        raise Http404
    # Show orders that contain items from this producer
    orders = Order.objects.filter(items__product__producer=request.user).distinct().order_by("-created_at")
    return render(request, "orders/manage_orders.html", {"orders": orders})


@login_required
def manage_order_detail(request, order_id):
    if not _is_producer(request.user):
        raise Http404
    
    # Must contain at least one item from this producer
    order = get_object_or_404(Order, id=order_id, items__product__producer=request.user)
    items = order.items.filter(product__producer=request.user)
    
    from marketplace.forms import OrderStatusForm
    if request.method == "POST":
        form = OrderStatusForm(request.POST, current_status=order.status)
        if form.is_valid():
            order.status = form.cleaned_data["status"]
            order.save(update_fields=["status"])
            return redirect("orders:manage_order_detail", order_id=order.id)
    else:
        form = OrderStatusForm(initial={"status": order.status}, current_status=order.status)
        
    return render(request, "orders/manage_order_detail.html", {
        "order": order,
        "items": items,
        "form": form
    })