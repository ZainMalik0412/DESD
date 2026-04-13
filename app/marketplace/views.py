import math
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.db.models import Q

from .models import Product, Category, Recipe, RecipeProduct, FarmStory, FavoriteRecipe, Order
from .forms import ProductForm, RecipeForm, FarmStoryForm
from accounts.models import CustomUser
from orders.views import _check_and_create_stock_alert


POSTCODE_COORDS = {
    # Bristol postcodes
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
    from django.db.models import Avg, Count
    
    products = Product.objects.filter(is_available=True).select_related('category', 'producer')
    
    # Annotate products with review statistics
    products = products.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews', distinct=True)
    )
    
    categories = Category.objects.filter(is_active=True)

    category_slug = request.GET.get('category')
    search = request.GET.get('search', '').strip()
    producer_name = request.GET.get('producer', '').strip()
    allergen_filter = request.GET.get('allergen_filter', '').strip()
    organic_certification = request.GET.get('organic_certification', '').strip()

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

    if organic_certification == Product.OrganicCertificationStatus.CERTIFIED_ORGANIC:
        products = products.filter(
            organic_certification_status=Product.OrganicCertificationStatus.CERTIFIED_ORGANIC
        )
    elif organic_certification == Product.OrganicCertificationStatus.NOT_CERTIFIED:
        products = products.filter(
            organic_certification_status=Product.OrganicCertificationStatus.NOT_CERTIFIED
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
        'organic_certification': organic_certification,
        'product_food_miles': product_food_miles,
    })


def producers(request):
    producers_qs = CustomUser.objects.filter(role='producer')
    return render(request, 'marketplace/producers.html', {'producers': producers_qs})


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    from .models import ProductReview

    customer_postcode = _get_customer_postcode(request.user)
    food_miles = calculate_food_miles(
        customer_postcode,
        getattr(product.producer, 'postcode', None)
    )
    
    # Get recipes that use this product
    linked_recipes = Recipe.objects.filter(
        linked_products__product=product,
        is_published=True
    ).distinct()
    
    # Get reviews for this product
    reviews = ProductReview.objects.filter(product=product).select_related('customer', 'order').order_by('-created_at')
    
    # Check if current user can review this product
    can_review = False
    has_reviewed = False
    if request.user.is_authenticated and request.user.role == CustomUser.Role.CUSTOMER:
        has_reviewed = ProductReview.objects.filter(product=product, customer=request.user).exists()
        if not has_reviewed:
            # Check if user has a delivered order with this product
            from orders.models import Order as OrdersModel
            can_review = OrdersModel.objects.filter(
                user=request.user,
                status=OrdersModel.STATUS_DELIVERED,
                items__product=product
            ).exists()
    
    # Calculate average rating and review count
    average_rating = product.get_average_rating()
    review_count = product.get_review_count()

    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'food_miles': food_miles,
        'linked_recipes': linked_recipes,
        'reviews': reviews,
        'can_review': can_review,
        'has_reviewed': has_reviewed,
        'average_rating': average_rating,
        'review_count': review_count,
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
                # Check and update stock alerts
                _check_and_create_stock_alert(product)
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
            # Refresh product from database to get latest values
            product.refresh_from_db()
            # Check and update stock alerts
            _check_and_create_stock_alert(product)
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


# RECIPE VIEWS

@login_required(login_url='/accounts/login/')
def my_recipes(request):
    """View for producers to see and manage their recipes."""
    if request.user.role != CustomUser.Role.PRODUCER:
        return redirect('/browse/')
    recipes = Recipe.objects.filter(producer=request.user).prefetch_related('linked_products__product')
    return render(request, 'marketplace/my_recipes.html', {'recipes': recipes})


@login_required(login_url='/accounts/login/')
def add_recipe(request):
    """View for producers to add a new recipe."""
    if request.user.role != CustomUser.Role.PRODUCER:
        return HttpResponseForbidden('You do not have permission to add recipes.')
    
    error = None
    success = None
    
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                recipe = form.save(commit=False)
                recipe.producer = request.user
                recipe.save()
                
                # Link products to recipe
                product_ids = request.POST.getlist('linked_products')
                for product_id in product_ids:
                    if product_id:
                        product = Product.objects.filter(id=product_id, producer=request.user).first()
                        if product:
                            RecipeProduct.objects.get_or_create(recipe=recipe, product=product)
                
                success = f'"{recipe.title}" has been added successfully!'
                form = RecipeForm()
            except Exception as e:
                error = f'Error adding recipe: {e}'
        else:
            error = 'Please correct the errors below.'
    else:
        form = RecipeForm()
    
    # Get producer's products for linking
    producer_products = Product.objects.filter(producer=request.user, is_available=True)
    
    return render(request, 'marketplace/add_recipe.html', {
        'form': form,
        'error': error,
        'success': success,
        'producer_products': producer_products,
    })


@login_required(login_url='/accounts/login/')
def edit_recipe(request, recipe_id):
    """View for producers to edit their recipes."""
    recipe = get_object_or_404(Recipe, id=recipe_id, producer=request.user)
    
    error = None
    success = None
    
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES, instance=recipe)
        if form.is_valid():
            try:
                recipe = form.save()
                
                # Update linked products
                RecipeProduct.objects.filter(recipe=recipe).delete()
                product_ids = request.POST.getlist('linked_products')
                for product_id in product_ids:
                    if product_id:
                        product = Product.objects.filter(id=product_id, producer=request.user).first()
                        if product:
                            RecipeProduct.objects.get_or_create(recipe=recipe, product=product)
                
                success = f'"{recipe.title}" has been updated successfully!'
            except Exception as e:
                error = f'Error updating recipe: {e}'
        else:
            error = 'Please correct the errors below.'
    else:
        form = RecipeForm(instance=recipe)
    
    # Get producer's products for linking
    producer_products = Product.objects.filter(producer=request.user, is_available=True)
    current_linked_products = recipe.linked_products.values_list('product_id', flat=True)
    
    return render(request, 'marketplace/edit_recipe.html', {
        'form': form,
        'recipe': recipe,
        'error': error,
        'success': success,
        'producer_products': producer_products,
        'current_linked_products': list(current_linked_products),
    })


@login_required(login_url='/accounts/login/')
def delete_recipe(request, recipe_id):
    """View for producers to delete their recipes."""
    recipe = get_object_or_404(Recipe, id=recipe_id, producer=request.user)
    
    if request.method == 'POST':
        recipe.delete()
        return redirect('my_recipes')
    
    return render(request, 'marketplace/delete_recipe.html', {'recipe': recipe})


def recipe_detail(request, recipe_id):
    """View for anyone to see a published recipe."""
    recipe = get_object_or_404(Recipe, id=recipe_id, is_published=True)
    linked_products = recipe.linked_products.select_related('product').all()
    
    # Check if current user has favorited this recipe
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = FavoriteRecipe.objects.filter(user=request.user, recipe=recipe).exists()
    
    return render(request, 'marketplace/recipe_detail.html', {
        'recipe': recipe,
        'linked_products': linked_products,
        'is_favorited': is_favorited,
    })


# FARM STORY VIEWS

@login_required(login_url='/accounts/login/')
def my_stories(request):
    """View for producers to see and manage their farm stories."""
    if request.user.role != CustomUser.Role.PRODUCER:
        return redirect('/browse/')
    stories = FarmStory.objects.filter(producer=request.user)
    return render(request, 'marketplace/my_stories.html', {'stories': stories})


@login_required(login_url='/accounts/login/')
def add_story(request):
    """View for producers to add a new farm story."""
    if request.user.role != CustomUser.Role.PRODUCER:
        return HttpResponseForbidden('You do not have permission to add stories.')
    
    error = None
    success = None
    
    if request.method == 'POST':
        form = FarmStoryForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                story = form.save(commit=False)
                story.producer = request.user
                story.save()
                success = f'"{story.title}" has been added successfully!'
                form = FarmStoryForm()
            except Exception as e:
                error = f'Error adding story: {e}'
        else:
            error = 'Please correct the errors below.'
    else:
        form = FarmStoryForm()
    
    return render(request, 'marketplace/add_story.html', {
        'form': form,
        'error': error,
        'success': success,
    })


@login_required(login_url='/accounts/login/')
def edit_story(request, story_id):
    """View for producers to edit their farm stories."""
    story = get_object_or_404(FarmStory, id=story_id, producer=request.user)
    
    error = None
    success = None
    
    if request.method == 'POST':
        form = FarmStoryForm(request.POST, request.FILES, instance=story)
        if form.is_valid():
            form.save()
            success = f'"{story.title}" has been updated successfully!'
        else:
            error = 'Please correct the errors below.'
    else:
        form = FarmStoryForm(instance=story)
    
    return render(request, 'marketplace/edit_story.html', {
        'form': form,
        'story': story,
        'error': error,
        'success': success,
    })


@login_required(login_url='/accounts/login/')
def delete_story(request, story_id):
    """View for producers to delete their farm stories."""
    story = get_object_or_404(FarmStory, id=story_id, producer=request.user)
    
    if request.method == 'POST':
        story.delete()
        return redirect('my_stories')
    
    return render(request, 'marketplace/delete_story.html', {'story': story})


def story_detail(request, story_id):
    """View for anyone to see a published farm story."""
    story = get_object_or_404(FarmStory, id=story_id, is_published=True)
    
    return render(request, 'marketplace/story_detail.html', {
        'story': story,
    })


def producer_profile(request, producer_id):
    """View for customers to see a producer's profile with stories and recipes."""
    producer = get_object_or_404(CustomUser, id=producer_id, role=CustomUser.Role.PRODUCER)
    stories = FarmStory.objects.filter(producer=producer, is_published=True)[:5]
    recipes = Recipe.objects.filter(producer=producer, is_published=True)[:5]
    products = Product.objects.filter(producer=producer, is_available=True)[:10]
    
    return render(request, 'marketplace/producer_profile.html', {
        'producer': producer,
        'stories': stories,
        'recipes': recipes,
        'products': products,
    })


def browse_recipes(request):
    """View for browsing all published recipes."""
    recipes = Recipe.objects.filter(is_published=True).select_related('producer')
    
    # Filter by seasonal tag if provided
    seasonal_tag = request.GET.get('season')
    if seasonal_tag:
        recipes = recipes.filter(seasonal_tag=seasonal_tag)
    
    return render(request, 'marketplace/browse_recipes.html', {
        'recipes': recipes,
        'seasonal_tag': seasonal_tag,
    })


def browse_stories(request):
    """View for browsing all published farm stories."""
    stories = FarmStory.objects.filter(is_published=True).select_related('producer')
    
    return render(request, 'marketplace/browse_stories.html', {
        'stories': stories,
    })


# FAVORITE RECIPE VIEWS

@login_required(login_url='/accounts/login/')
def toggle_favorite_recipe(request, recipe_id):
    """Toggle a recipe as favorite for the current user."""
    recipe = get_object_or_404(Recipe, id=recipe_id, is_published=True)
    
    # Check if already favorited
    favorite = FavoriteRecipe.objects.filter(user=request.user, recipe=recipe).first()
    
    if favorite:
        # Unfavorite
        favorite.delete()
        favorited = False
    else:
        # Favorite
        FavoriteRecipe.objects.create(user=request.user, recipe=recipe)
        favorited = True
    
    # If AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'favorited': favorited})
    
    # Otherwise redirect back to the recipe
    return redirect('recipe_detail', recipe_id=recipe_id)


@login_required(login_url='/accounts/login/')
def my_favorite_recipes(request):
    """View for customers to see their saved favorite recipes."""
    favorites = FavoriteRecipe.objects.filter(user=request.user).select_related('recipe__producer')
    
    return render(request, 'marketplace/my_favorite_recipes.html', {
        'favorites': favorites,
    })


# PRODUCT REVIEW VIEWS

@login_required(login_url='/accounts/login/')
def submit_review(request, product_id):
    """View for customers to submit a review for a purchased product."""
    from .models import ProductReview
    from .forms import ProductReviewForm
    
    product = get_object_or_404(Product, id=product_id)
    
    # Check if user has already reviewed this product
    existing_review = ProductReview.objects.filter(product=product, customer=request.user).first()
    if existing_review:
        return render(request, 'marketplace/review_error.html', {
            'error_message': 'You have already reviewed this product. You can edit your existing review instead.',
            'review': existing_review,
        })
    
    # Find delivered orders containing this product
    from orders.models import Order as OrdersModel
    delivered_orders = OrdersModel.objects.filter(
        user=request.user,
        status=OrdersModel.STATUS_DELIVERED,
        items__product=product
    ).distinct()
    
    if not delivered_orders.exists():
        return render(request, 'marketplace/review_error.html', {
            'error_message': 'You can only review products you have purchased and received. This order must be marked as delivered.',
            'product': product,
        })
    
    # Use the most recent delivered order for the review
    order = delivered_orders.order_by('-created_at').first()
    
    error = None
    success = None
    
    if request.method == 'POST':
        form = ProductReviewForm(request.POST)
        if form.is_valid():
            try:
                review = form.save(commit=False)
                review.product = product
                review.customer = request.user
                review.order = order
                review.save()
                success = f'Your review for "{product.name}" has been submitted successfully!'
                return redirect('product_detail', product_id=product_id)
            except Exception as e:
                error = f'Error submitting review: {e}'
        else:
            error = 'Please correct the errors below.'
    else:
        form = ProductReviewForm()
    
    return render(request, 'marketplace/submit_review.html', {
        'form': form,
        'product': product,
        'order': order,
        'error': error,
        'success': success,
    })


@login_required(login_url='/accounts/login/')
def edit_review(request, review_id):
    """View for customers to edit their existing review."""
    from .models import ProductReview
    from .forms import ProductReviewForm
    
    review = get_object_or_404(ProductReview, id=review_id, customer=request.user)
    
    error = None
    success = None
    
    if request.method == 'POST':
        form = ProductReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            success = f'Your review for "{review.product.name}" has been updated successfully!'
            return redirect('product_detail', product_id=review.product.id)
        else:
            error = 'Please correct the errors below.'
    else:
        form = ProductReviewForm(instance=review)
    
    return render(request, 'marketplace/edit_review.html', {
        'form': form,
        'review': review,
        'error': error,
        'success': success,
    })


@login_required(login_url='/accounts/login/')
def delete_review(request, review_id):
    """View for customers to delete their review."""
    from .models import ProductReview
    
    review = get_object_or_404(ProductReview, id=review_id, customer=request.user)
    product_id = review.product.id
    
    if request.method == 'POST':
        review.delete()
        return redirect('product_detail', product_id=product_id)
    
    return render(request, 'marketplace/delete_review.html', {'review': review})


@login_required(login_url='/accounts/login/')
def producer_respond_review(request, review_id):
    """View for producers to respond to reviews on their products."""
    from .models import ProductReview
    from django.utils import timezone
    
    review = get_object_or_404(ProductReview, id=review_id, product__producer=request.user)
    
    error = None
    success = None
    
    if request.method == 'POST':
        response_text = request.POST.get('producer_response', '').strip()
        
        if not response_text:
            error = 'Response cannot be empty.'
        else:
            try:
                review.producer_response = response_text
                review.producer_response_date = timezone.now()
                review.save()
                success = 'Your response has been posted successfully!'
                return redirect('product_detail', product_id=review.product.id)
            except Exception as e:
                error = f'Error posting response: {e}'
    
    return render(request, 'marketplace/producer_respond_review.html', {
        'review': review,
        'error': error,
        'success': success,
    })


@login_required(login_url='/accounts/login/')
def my_reviews(request):
    """View for customers to see all their reviews."""
    from .models import ProductReview
    
    reviews = ProductReview.objects.filter(customer=request.user).select_related('product', 'order')
    
    return render(request, 'marketplace/my_reviews.html', {
        'reviews': reviews,
    })