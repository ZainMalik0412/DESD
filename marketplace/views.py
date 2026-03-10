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

    category_list = list(categories)
    for cat in category_list:
        cat.is_selected = (category_slug == cat.slug)

    return render(request, 'marketplace/browse.html', {
        'products': products,
        'categories': category_list,
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
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'marketplace/product_detail.html', {'product': product})


from .forms import ProductForm

@login_required(login_url='/accounts/login/')
def add_product(request):
    """Add new product page - allows producers to add new products."""
    # Only producers can add products
    if request.user.role != 'producer':
        return redirect('/browse/')

    error = None
    success = None

    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            try:
                # Don't save to DB yet, we need to attach the producer
                product = form.save(commit=False)
                product.producer = request.user
                product.save()
                success = f'"{product.name}" has been added successfully!'
                # Clear the form after successful submission
                form = ProductForm()
            except Exception as e:
                error = f'Error adding product: {e}'
        else:
            # The form contains validation errors
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
    """Change product information page - allows producers to update their products."""
    product = get_object_or_404(Product, id=product_id, producer=request.user)

    error = None
    success = None

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
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
    """Delete a product - only the producer who owns it can delete it."""
    product = get_object_or_404(Product, id=product_id, producer=request.user)

    if request.method == 'POST':
        product.delete()
        return redirect('/browse/')

    return render(request, 'marketplace/delete_product.html', {'product': product})


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
