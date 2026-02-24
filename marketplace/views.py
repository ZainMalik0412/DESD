from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from marketplace.models import Product, Category
from accounts.models import CustomUser


def browse(request):
    products = Product.objects.filter(is_available=True).select_related('category', 'producer')
    categories = Category.objects.filter(is_active=True)

    category_slug = request.GET.get('category')
    search = request.GET.get('search', '').strip()

    if category_slug:
        products = products.filter(category__slug=category_slug)
    if search:
        products = products.filter(name__icontains=search)

    return render(request, 'marketplace/browse.html', {
        'products': products,
        'categories': categories,
        'search': search,
        'selected_category': category_slug,
    })


def producers(request):
    # Show ALL users with producer role, not just those with products
    producers_qs = CustomUser.objects.filter(role='producer')
    return render(request, 'marketplace/producers.html', {'producers': producers_qs})


@login_required(login_url='/accounts/login/')
def add_product(request):
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
