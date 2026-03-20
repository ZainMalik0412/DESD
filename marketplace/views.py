import math
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.db.models import Q

from .models import Product, Category
from .forms import ProductForm
from accounts.models import CustomUser


POSTCODE_COORDS = {
    'BS1': (51.4545, -2.5879),
    'BA1': (51.3811, -2.3590),
    'EX1': (50.7260, -3.5270),
}


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
    if not getattr(user, 'is_authenticated', False):
        return None
    if getattr(user, 'role', None) != CustomUser.Role.CUSTOMER:
        return None
    return getattr(user, 'postcode', None)


# PAGE VIEWS

def browse(request):
    products = Product.objects.filter(is_available=True).select_related('category', 'producer')
    categories = Category.objects.filter(is_active=True)

    category_slug = request.GET.get('category')
    search = request.GET.get('search', '').strip()
    producer_name = request.GET.get('producer', '').strip()
    allergen_filter = request.GET.get('allergen_filter', '').strip()

    if category_slug:
        products = products.filter(category__slug=category_slug)

    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(allergen_info__icontains=search)
        )

    if producer_name:
        products = products.filter(producer__username=producer_name)

    if allergen_filter == 'has_allergens':
        products = products.exclude(allergen_info__isnull=True).exclude(allergen_info__exact='')
    elif allergen_filter == 'no_allergens':
        products = products.filter(
            Q(allergen_info__isnull=True) | Q(allergen_info__exact='')
        )

    category_list = list(categories)
    for cat in category_list:
        cat.is_selected = (category_slug == cat.slug)

    customer_postcode = _get_customer_postcode(request.user)
    product_food_miles = {}

    for product in products:
        miles = calculate_food_miles(
            customer_postcode,
            getattr(product.producer, 'postcode', None)
        )
        product.food_miles = miles
        product_food_miles[product.id] = miles

    return render(request, 'marketplace/browse.html', {
        'products': products,
        'categories': category_list,
        'search': search,
        'selected_category': category_slug,
        'producer_name': producer_name,
        'allergen_filter': allergen_filter,
        'product_food_miles': product_food_miles,
    })


def producers(request):
    producers_qs = CustomUser.objects.filter(role='producer')
    return render(request, 'marketplace/producers.html', {'producers': producers_qs})


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    customer_postcode = _get_customer_postcode(request.user)
    food_miles = calculate_food_miles(
        customer_postcode,
        getattr(product.producer, 'postcode', None)
    )

    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'food_miles': food_miles,
    })


@login_required(login_url='/accounts/login/')
def my_products(request):
    if request.user.role != 'producer':
        return redirect('/browse/')
    products = Product.objects.filter(producer=request.user).order_by('-created_at')
    return render(request, 'marketplace/my_products.html', {'products': products})


@login_required(login_url='/accounts/login/')
def add_product(request):
    if request.user.role != CustomUser.Role.PRODUCER:
        return HttpResponseForbidden('You do not have permission to add products.')

    error = None
    success = None

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                product = form.save(commit=False)
                product.producer = request.user
                product.save()
                success = f'"{product.name}" has been added successfully!'
                form = ProductForm()
            except Exception as e:
                error = f'Error adding product: {e}'
        else:
            error = 'Please correct the errors below.'
    else:
        form = ProductForm()

    return render(request, 'marketplace/add_product.html', {
        'form': form,
        'error': error,
        'success': success,
    })


@login_required(login_url='/accounts/login/')
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, producer=request.user)

    error = None
    success = None

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            success = f'"{product.name}" has been updated successfully!'
        else:
            error = 'Please correct the errors below.'
    else:
        form = ProductForm(instance=product)

    return render(request, 'marketplace/edit_product.html', {
        'form': form,
        'product': product,
        'error': error,
        'success': success,
    })


@login_required(login_url='/accounts/login/')
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, producer=request.user)

    if request.method == 'POST':
        product.delete()
        return redirect('/browse/')

    return render(request, 'marketplace/delete_product.html', {'product': product})


@login_required
def place_order(request):
    pass


# HELPER FUNCTIONS

@login_required
def add_to_basket(request, product_id):
    pass


@login_required
def cancel_order(request, order_id):
    pass


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


def record_audit(action, user, details):
    pass


def calculate_commission(order_total, user_role):
    pass


def send_payment_request(order, payment_processor):
    pass


def update_inventory(product_id, quantity_change):
    pass


def generate_report(report_type, filters):
    pass