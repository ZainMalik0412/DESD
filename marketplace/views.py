from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from .models import Product, Category
from accounts.models import CustomUser

# PAGE VIEWS

def browse(request):
    products = Product.objects.filter(is_available=True).select_related('category', 'producer')
    categories = Category.objects.filter(is_active=True)

    category_slug = request.GET.get('category')
    search = request.GET.get('search', '').strip()
    producer_name = request.GET.get('producer', '').strip()

    if category_slug:
        products = products.filter(category__slug=category_slug)
    if search:
        products = products.filter(name__icontains=search)
    if producer_name:
        products = products.filter(producer__username=producer_name)

    return render(request, 'marketplace/browse.html', {
        'products': products,
        'categories': categories,
        'search': search,
        'selected_category': category_slug,
        'producer_name': producer_name,
    })


def producers(request):
    # Show ALL users with producer role, not just those with products
    producers_qs = CustomUser.objects.filter(role='producer')
    return render(request, 'marketplace/producers.html', {'producers': producers_qs})


def product_detail(request, product_id):
    """Product detail page - displays detailed information about a single product."""
    pass


@login_required(login_url='/accounts/login/')
def add_product(request):
    """Add new product page - allows producers to add new products."""
    # Only producers can add products
    if request.user.role != 'producer':
        return redirect('/browse/')

    categories = Category.objects.filter(is_active=True)
    error = None
    success = None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        unit = request.POST.get('unit', 'item')
        stock = request.POST.get('stock_quantity', 0)

        if not name or not price or not category_id:
            error = 'Please fill in all required fields.'
        else:
            try:
                category = Category.objects.get(id=category_id)
                Product.objects.create(
                    name=name,
                    description=description,
                    category=category,
                    producer=request.user,
                    price=price,
                    unit=unit,
                    stock_quantity=stock,
                    is_available=True,
                )
                success = f'"{name}" has been added successfully!'
            except Category.DoesNotExist:
                error = 'Invalid category selected.'
            except Exception as e:
                error = f'Error adding product: {e}'

    return render(request, 'marketplace/add_product.html', {
        'categories': categories,
        'units': Product.Unit.choices,
        'error': error,
        'success': success,
    })


@login_required
def edit_product(request, product_id):
    """Change product information page - allows producers to update their products."""
    pass


@login_required
def place_order(request):
    """Place order page - processes customer order from basket."""
    pass


# HELPER FUNCTIONS

@login_required
def add_to_basket(request, product_id):
    """Helper function - adds a product to user's shopping basket."""
    pass


@login_required
def cancel_order(request, order_id):
    """Helper function - cancels an existing order."""
    pass


def calculate_food_miles(origin, destination):
    """Helper function - calculates distance between producer and customer."""
    pass


def record_audit(action, user, details):
    """Helper function - records audit trail for important actions."""
    pass


def calculate_commission(order_total, user_role):
    """Helper function - calculates platform commission based on order and user type."""
    pass


def send_payment_request(order, payment_processor):
    """Helper function - sends payment request to external payment processor."""
    pass


def update_inventory(product_id, quantity_change):
    """Helper function - updates product stock levels."""
    pass


def generate_report(report_type, filters):
    """Helper function - generates various reports (sales, inventory, etc.)."""
    pass
