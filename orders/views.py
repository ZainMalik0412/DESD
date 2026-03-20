import math
import re
import stripe
from collections import OrderedDict
from decimal import Decimal
from datetime import datetime, date, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from marketplace.models import Product
from .models import Cart, CartItem, Order, OrderItem, StatusUpdate


POSTCODE_COORDS = {
    'BS1': (51.4545, -2.5879),
    'BA1': (51.3811, -2.3590),
    'EX1': (50.7260, -3.5270),
}


def _is_customer(user):
    role = getattr(user, "role", None)
    return role in (None, "customer")


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user, status=Cart.STATUS_ACTIVE)
    return cart


def _get_outward_code(postcode):
    if not postcode:
        return None

    postcode = postcode.strip().upper()
    match = re.match(r'^([A-Z]{1,2}\d[A-Z\d]?)', postcode)
    if match:
        return match.group(1)

    parts = postcode.split()
    return parts[0] if parts else None


def _get_coords_from_postcode(postcode):
    outward = _get_outward_code(postcode)
    if not outward:
        return None
    return POSTCODE_COORDS.get(outward)


def _haversine_miles(lat1, lon1, lat2, lon2):
    radius_miles = 3958.8

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return radius_miles * c


def _get_customer_postcode(user):
    if not getattr(user, "is_authenticated", False):
        return None
    if not _is_customer(user):
        return None
    return getattr(user, "postcode", None)


def calculate_food_miles(origin, destination):
    if not origin or not destination:
        return None

    origin_coords = _get_coords_from_postcode(origin)
    destination_coords = _get_coords_from_postcode(destination)

    if origin_coords and destination_coords:
        miles = _haversine_miles(
            origin_coords[0],
            origin_coords[1],
            destination_coords[0],
            destination_coords[1],
        )
        return round(miles, 1)

    origin_outward = _get_outward_code(origin)
    destination_outward = _get_outward_code(destination)

    if not origin_outward or not destination_outward:
        return None

    if origin_outward == destination_outward:
        return 1.0

    origin_area = re.match(r'^[A-Z]+', origin_outward)
    destination_area = re.match(r'^[A-Z]+', destination_outward)

    if origin_area and destination_area and origin_area.group(0) == destination_area.group(0):
        return 15.0

    return 60.0


def _group_cart_items_by_producer(items):
    grouped = OrderedDict()
    for item in items:
        producer = item.product.producer
        if producer.id not in grouped:
            grouped[producer.id] = {"producer": producer, "items": [], "subtotal": Decimal("0.00")}
        grouped[producer.id]["items"].append(item)
        grouped[producer.id]["subtotal"] += item.line_total
    return list(grouped.values())


def _group_order_items_by_producer(items):
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
    items = list(cart.items.select_related("product", "product__producer").all())

    item_food_miles = {}
    total_food_miles = 0.0

    for item in items:
        item.food_miles = None

        customer_postcode = getattr(request.user, "postcode", None)
        producer_postcode = getattr(item.product.producer, "postcode", None)

        if customer_postcode and producer_postcode:
            miles = calculate_food_miles(producer_postcode, customer_postcode)
            if miles is not None:
                miles = round(miles, 1)
                item.food_miles = miles
                item_food_miles[item.product.id] = miles
                total_food_miles += miles

    grouped_items = _group_cart_items_by_producer(items)

    return render(request, "orders/cart.html", {
        "cart": cart,
        "items": items,
        "grouped_items": grouped_items,
        "item_food_miles": item_food_miles,
        "total_food_miles": round(total_food_miles, 1),
    })


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
            "cart": cart,
            "items": items,
            "grouped_items": grouped_items,
            "commission": commission,
            "grand_total": grand_total,
        })

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

    request.session["checkout_details"] = {
        "full_name": request.POST.get("full_name", "").strip(),
        "email": request.POST.get("email", "").strip(),
        "address_line1": request.POST.get("address_line1", "").strip(),
        "address_line2": request.POST.get("address_line2", "").strip(),
        "city": request.POST.get("city", "").strip(),
        "postcode": request.POST.get("postcode", "").strip(),
        "delivery_date": raw_delivery_date,
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

        raw_delivery_date = details.get("delivery_date", "")
        try:
            parsed_date = datetime.strptime(raw_delivery_date, "%Y-%m-%d").date()
        except ValueError:
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
            delivery_date=parsed_date,
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
        commission_amount = (total * Order.COMMISSION_RATE).quantize(Decimal("0.01"))
        order.commission = commission_amount
        order.save(update_fields=["total", "commission"])

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
    items = order.items.select_related("product", "product__producer").all()
    grouped_items = _group_order_items_by_producer(items)
    status_updates = order.status_updates.all()
    return render(request, "orders/order_detail.html", {
        "order": order,
        "items": items,
        "grouped_items": grouped_items,
        "status_updates": status_updates,
    })


def _is_producer(user):
    return getattr(user, "role", None) == "producer"


@login_required
def manage_orders(request):
    if not _is_producer(request.user):
        raise Http404
    orders = Order.objects.filter(items__product__producer=request.user).distinct().order_by("delivery_date", "-created_at")
    return render(request, "orders/manage_orders.html", {"orders": orders})


@login_required
def manage_order_detail(request, order_id):
    if not _is_producer(request.user):
        raise Http404

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