import csv
import math
import re
import stripe
from collections import OrderedDict
from decimal import Decimal
from datetime import datetime, date, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from marketplace.models import Product, StockAlert
from .models import Cart, CartItem, Order, OrderItem, StatusUpdate
from .notifications import send_order_confirmation_email, send_status_update_email


POSTCODE_COORDS = {
    'BS1': (51.4545, -2.5879),  # Bristol City Centre
    'BS2': (51.4550, -2.5750),  # Bristol East
    'BS3': (51.4380, -2.6020),  # Bedminster
    'BS4': (51.4340, -2.5530),  # Knowle/Brislington
    'BS5': (51.4620, -2.5330),  # Eastville/St George
    'BS6': (51.4750, -2.6020),  # Redland/Cotham
    'BS7': (51.4840, -2.5830),  # Horfield/Bishopston
    'BS8': (51.4630, -2.6170),  # Clifton
    'BS9': (51.4880, -2.6290),  # Stoke Bishop
    'BS10': (51.5160, -2.5960), # Southmead/Henbury
    'BS11': (51.4930, -2.6830), # Shirehampton/Avonmouth
    'BS13': (51.4180, -2.6170), # Hartcliffe/Withywood
    'BS14': (51.4030, -2.5470), # Stockwood/Hengrove
    'BS15': (51.4530, -2.4850), # Kingswood/Hanham
    'BS16': (51.4850, -2.5050), # Downend/Fishponds
    'BS20': (51.4870, -2.7540), # Portishead
    'BS30': (51.4410, -2.4930), # Warmley
    'BS31': (51.3670, -2.4850), # Keynsham
    'BS32': (51.5370, -2.5520), # Bradley Stoke/Aztec West
    'BS34': (51.5460, -2.5180), # Filton/Patchway
    'BS35': (51.5380, -2.4770), # Thornbury
    'BS36': (51.5170, -2.4730), # Winterbourne
    'BS37': (51.5590, -2.4650), # Yate/Chipping Sodbury
    'BS39': (51.3260, -2.5480), # Farrington Gurney
    'BS40': (51.3640, -2.6740), # Chew Magna
    'BS41': (51.4150, -2.7070), # Long Ashton
    'BS48': (51.3940, -2.7910), # Nailsea
    'BS49': (51.4360, -2.8310) # Winscombe
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


def _sanitize_csv_field(value):
    """
    Sanitize CSV field to prevent CSV injection attacks.
    Formulas starting with =, +, -, @, tab, or carriage return can execute in Excel.
    """
    if not value:
        return ""
    
    value_str = str(value).strip()
    
    # If field starts with dangerous characters, prefix with single quote
    if value_str and value_str[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + value_str
    
    return value_str


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


def _check_and_create_stock_alert(product):
    """
    Check if product stock is below threshold and create/resolve alerts accordingly.
    """
    if product.stock_quantity < product.low_stock_threshold:
        # Check if there's already an active alert for this product
        if not StockAlert.objects.filter(
            product=product,
            status=StockAlert.Status.ACTIVE
        ).exists():
            # Create new alert
            StockAlert.objects.create(
                product=product,
                producer=product.producer,
                stock_level=product.stock_quantity,
                threshold=product.low_stock_threshold,
                status=StockAlert.Status.ACTIVE
            )
    else:
        # Stock is above threshold, resolve any active alerts
        StockAlert.objects.filter(
            product=product,
            status=StockAlert.Status.ACTIVE
        ).update(status=StockAlert.Status.RESOLVED)


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


def _get_previous_week_window():
    """
    Calculate the previous week's date range (Sunday to Saturday).
    
    Returns:
        tuple: (previous_week_start, previous_week_end) where end is exclusive
    """
    today = timezone.localdate()
    # Calculate days since last Sunday (where Sunday = 0, Monday = 1, etc.)
    # weekday() returns Mon=0, so we adjust: (weekday() + 1) % 7 gives Sun=0, Mon=1, etc.
    days_since_sunday = (today.weekday() + 1) % 7
    current_week_start = today - timedelta(days=days_since_sunday)  # Sunday of current week
    previous_week_start = current_week_start - timedelta(days=7)  # Sunday of previous week
    previous_week_end = current_week_start  # Sunday of current week (exclusive)
    return previous_week_start, previous_week_end


def _get_tax_year_start():
    today = timezone.localdate()
    if (today.month, today.day) >= (4, 6):
        return date(today.year, 4, 6)
    return date(today.year - 1, 4, 6)


def _get_weekly_settlement_queryset(producer):
    previous_week_start, previous_week_end = _get_previous_week_window()
    return (
        Order.objects.filter(
            status=Order.STATUS_DELIVERED,
            created_at__date__gte=previous_week_start,
            created_at__date__lt=previous_week_end,
            items__product__producer=producer,
        )
        .distinct()
        .prefetch_related("items__product__producer")
        .order_by("created_at", "id")
    )


def _build_producer_settlement_rows(orders, producer):
    rows = []
    total_orders_value = Decimal("0.00")

    for order in orders:
        producer_items = []
        producer_total = Decimal("0.00")

        for item in order.items.all():
            item_producer = item.product.producer if item.product else None
            if item_producer == producer:
                producer_items.append(item)
                producer_total += item.line_total

        if producer_total == Decimal("0.00"):
            continue

        commission = (producer_total * Order.COMMISSION_RATE).quantize(Decimal("0.01"))
        producer_payment = (producer_total - commission).quantize(Decimal("0.01"))

        rows.append({
            "order": order,
            "items": producer_items,
            "order_total": producer_total.quantize(Decimal("0.01")),
            "commission": commission,
            "producer_payment": producer_payment,
        })
        total_orders_value += producer_total

    total_orders_value = total_orders_value.quantize(Decimal("0.01"))
    total_commission = (total_orders_value * Order.COMMISSION_RATE).quantize(Decimal("0.01"))
    total_producer_payment = (total_orders_value - total_commission).quantize(Decimal("0.01"))

    return rows, total_orders_value, total_commission, total_producer_payment


def _get_tax_year_total_for_producer(producer):
    tax_year_start = _get_tax_year_start()
    delivered_orders = (
        Order.objects.filter(
            status=Order.STATUS_DELIVERED,
            created_at__date__gte=tax_year_start,
            items__product__producer=producer,
        )
        .distinct()
        .prefetch_related("items__product__producer")
    )

    total = Decimal("0.00")
    for order in delivered_orders:
        for item in order.items.all():
            item_producer = item.product.producer if item.product else None
            if item_producer == producer:
                total += item.line_total

    return total.quantize(Decimal("0.01"))


def _get_payment_status(rows):
    return "Processed" if rows else "Pending Bank Transfer"


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
    messages.success(request, f"Successfully added {qty}x {product.name} to your cart.")

    next_url = request.META.get("HTTP_REFERER", "orders:cart")
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
            if p.stock_quantity < i.quantity:
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
            status=Order.STATUS_CONFIRMED,
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

            # Decrement stock quantity
            p.stock_quantity -= i.quantity
            
            # Mark as unavailable if out of stock
            if p.stock_quantity <= 0:
                p.is_available = False
                p.save(update_fields=["stock_quantity", "is_available"])
            else:
                p.save(update_fields=["stock_quantity"])

            # Check if stock alert should be created
            _check_and_create_stock_alert(p)

            total += line_total

        order.total = total
        commission_amount = (total * Order.COMMISSION_RATE).quantize(Decimal("0.01"))
        order.commission = commission_amount
        order.save(update_fields=["total", "commission"])

        cart.status = Cart.STATUS_CONVERTED
        cart.save(update_fields=["status"])
        cart.items.all().delete()

    send_order_confirmation_email(order)

    return redirect("orders:order_detail", order_id=order.id)


@login_required
def stripe_cancel(request):
    return redirect("orders:checkout")


@login_required
def order_list(request):
    if not _is_customer(request.user):
        raise Http404
    orders = request.user.orders.prefetch_related("items__product__producer").order_by("-created_at")
    
    # Add producer names to each order
    for order in orders:
        producers = set()
        for item in order.items.all():
            if item.product and item.product.producer:
                producers.add(item.product.producer.username)
        order.producer_names = ", ".join(sorted(producers)) if producers else "N/A"
    
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


@login_required
def reorder(request, order_id):
    """Add all items from a previous order to the current cart."""
    if not _is_customer(request.user):
        raise Http404
    
    if request.method != "POST":
        return redirect("orders:order_detail", order_id=order_id)
    
    order = get_object_or_404(Order, id=order_id, user=request.user)
    cart = _get_cart(request.user)
    
    from django.contrib import messages
    
    added_count = 0
    unavailable_products = []
    
    for order_item in order.items.all():
        product = order_item.product
        
        # Check if product still exists and is available
        if not product:
            unavailable_products.append(order_item.product_name)
            continue
        
        if not product.is_available:
            unavailable_products.append(product.name)
            continue
        
        # Add to cart
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        cart_item.quantity = order_item.quantity if created else cart_item.quantity + order_item.quantity
        cart_item.save()
        added_count += 1
    
    if added_count > 0:
        messages.success(request, f"Successfully added {added_count} item(s) from order #{order.id} to your cart.")
    
    if unavailable_products:
        messages.warning(
            request,
            f"The following products are no longer available: {', '.join(unavailable_products)}"
        )
    
    return redirect("orders:cart")


@login_required
def download_receipt(request, order_id):
    """Download order receipt as CSV."""
    if not _is_customer(request.user):
        raise Http404
    
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.items.select_related("product", "product__producer").all()
    
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="order_{order.id}_receipt.csv"'
    
    writer = csv.writer(response)
    
    # Header information
    writer.writerow(["Bristol Regional Food Network"])
    writer.writerow(["Order Receipt"])
    writer.writerow([])
    writer.writerow(["Order Number:", order.id])
    writer.writerow(["Order Date:", order.created_at.strftime("%d %B %Y, %H:%M")])
    if order.delivery_date:
        writer.writerow(["Delivery Date:", order.delivery_date.strftime("%d %B %Y")])
    writer.writerow(["Status:", order.get_status_display()])
    writer.writerow([])
    
    # Delivery address
    writer.writerow(["Delivery Address:"])
    writer.writerow([_sanitize_csv_field(order.full_name)])
    writer.writerow([_sanitize_csv_field(order.address_line1)])
    if order.address_line2:
        writer.writerow([_sanitize_csv_field(order.address_line2)])
    writer.writerow([_sanitize_csv_field(f"{order.city}, {order.postcode}")])
    writer.writerow([_sanitize_csv_field(order.email)])
    writer.writerow([])
    
    # Items header
    writer.writerow(["Product", "Producer", "Price", "Quantity", "Total"])
    
    # Group items by producer
    grouped_items = _group_order_items_by_producer(items)
    
    for group in grouped_items:
        for item in group["items"]:
            producer_name = group["producer"].username if group["producer"] else "Unknown"
            writer.writerow([
                _sanitize_csv_field(item.product_name),
                _sanitize_csv_field(producer_name),
                f"£{item.unit_price:.2f}",
                item.quantity,
                f"£{item.line_total:.2f}"
            ])
        
        writer.writerow([])
        writer.writerow(["", "", "", "Subtotal:", f"£{group['subtotal']:.2f}"])
        writer.writerow([])
    
    # Total
    writer.writerow(["", "", "", "Order Total:", f"£{order.total:.2f}"])
    
    if order.commission:
        writer.writerow(["", "", "", "Network Commission (5%):", f"£{order.commission:.2f}"])
    
    return response


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

                send_status_update_email(order, old_status, new_status, note)

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


@login_required
def stock_alerts(request):
    """
    Display low stock alerts for producers.
    """
    if not _is_producer(request.user):
        raise Http404

    # Handle alert dismissal
    if request.method == "POST":
        alert_id = request.POST.get("alert_id")
        action = request.POST.get("action")
        
        if alert_id and action == "dismiss":
            StockAlert.objects.filter(
                id=alert_id,
                producer=request.user,
                status=StockAlert.Status.ACTIVE
            ).update(status=StockAlert.Status.DISMISSED)
            
            from django.contrib import messages
            messages.success(request, "Alert dismissed.")
            
            return redirect("orders:stock_alerts")

    # Get all alerts for this producer
    active_alerts = StockAlert.objects.filter(
        producer=request.user,
        status=StockAlert.Status.ACTIVE
    ).select_related("product").order_by("-created_at")
    
    resolved_alerts = StockAlert.objects.filter(
        producer=request.user,
        status__in=[StockAlert.Status.RESOLVED, StockAlert.Status.DISMISSED]
    ).select_related("product").order_by("-updated_at")[:10]  # Last 10 resolved

    return render(request, "orders/stock_alerts.html", {
        "active_alerts": active_alerts,
        "resolved_alerts": resolved_alerts,
    })


@login_required
def payments(request):
    if not _is_producer(request.user):
        raise Http404

    weekly_orders = _get_weekly_settlement_queryset(request.user)
    settlement_rows, total_orders_value, total_commission, total_producer_payment = _build_producer_settlement_rows(
        weekly_orders, request.user
    )
    payment_status = _get_payment_status(settlement_rows)
    tax_year_total = _get_tax_year_total_for_producer(request.user)
    previous_week_start, previous_week_end = _get_previous_week_window()

    return render(request, "orders/payments.html", {
        "settlement_rows": settlement_rows,
        "total_orders_value": total_orders_value,
        "total_commission": total_commission,
        "total_producer_payment": total_producer_payment,
        "payment_status": payment_status,
        "tax_year_total": tax_year_total,
        "previous_week_start": previous_week_start,
        "previous_week_end": previous_week_end - timedelta(days=1),
    })


@login_required
def payments_report_csv(request):
    if not _is_producer(request.user):
        raise Http404

    weekly_orders = _get_weekly_settlement_queryset(request.user)
    settlement_rows, total_orders_value, total_commission, total_producer_payment = _build_producer_settlement_rows(weekly_orders, request.user)
    payment_status = _get_payment_status(settlement_rows)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="weekly_payment_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "order_id",
        "customer_name",
        "items",
        "order_total",
        "commission",
        "producer_payment",
        "payment_status",
    ])

    for row in settlement_rows:
        # Sanitize all fields to prevent CSV injection
        customer_name = _sanitize_csv_field(row["order"].full_name)
        items_list = "; ".join(_sanitize_csv_field(item.product_name) for item in row["items"])
        
        writer.writerow([
            row["order"].id,
            customer_name,
            items_list,
            f"{row['order_total']:.2f}",
            f"{row['commission']:.2f}",
            f"{row['producer_payment']:.2f}",
            payment_status,
        ])

    writer.writerow([])
    writer.writerow([
        "totals",
        "",
        "",
        f"{total_orders_value:.2f}",
        f"{total_commission:.2f}",
        f"{total_producer_payment:.2f}",
        payment_status,
    ])

    return response