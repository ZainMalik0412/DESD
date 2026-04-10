from django.conf import settings
from django.db import models
from .services.file_validators import (
    validate_image_file_extension,
    validate_image_file_size,
    validate_image_content_type,
)


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    class Unit(models.TextChoices):
        ITEM = "item", "Item"
        KG = "kg", "kg"
        G = "g", "g"
        L = "l", "L"
        ML = "ml", "ml"
        BUNCH = "bunch", "Bunch"
        PACK = "pack", "Pack"
        DOZEN = "dozen", "Dozen"

    class SeasonalStatus(models.TextChoices):
        IN_SEASON = "in_season", "In Season"
        OUT_OF_SEASON = "out_of_season", "Out of Season"
        ALL_YEAR = "all_year", "Available All Year"
        LIMITED = "limited", "Limited Availability"

    class OrganicCertificationStatus(models.TextChoices):
        CERTIFIED_ORGANIC = "certified_organic", "Certified Organic"
        NOT_CERTIFIED = "not_certified", "Not Certified"

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    producer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products")

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.ITEM)
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        help_text="Alert when stock falls below this level"
    )
    is_available = models.BooleanField(default=True)
    seasonal_status = models.CharField(
        max_length=20,
        choices=SeasonalStatus.choices,
        default=SeasonalStatus.ALL_YEAR,
    )
    organic_certification_status = models.CharField(
        max_length=25,
        choices=OrganicCertificationStatus.choices,
        default=OrganicCertificationStatus.NOT_CERTIFIED,
    )
    allergen_info = models.TextField(blank=True, help_text="List any allergens, e.g. Contains eggs")
    harvest_date = models.DateField(null=True, blank=True, help_text="Date of harvest or production")
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
        validators=[validate_image_file_extension, validate_image_file_size, validate_image_content_type]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("producer", "name")

    def __str__(self):
        return f"{self.name} - {self.producer.username}"
    
    def get_average_rating(self):
        """Calculate the average rating for this product."""
        from django.db.models import Avg
        result = self.reviews.aggregate(avg_rating=Avg('rating'))
        return result['avg_rating'] or 0
    
    def get_review_count(self):
        """Get the total number of reviews for this product."""
        return self.reviews.count()


class Basket(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="basket")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Basket for {self.user.username}"

    def get_total(self):
        return sum(item.get_subtotal() for item in self.items.all())


class BasketItem(models.Model):
    basket = models.ForeignKey(Basket, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("basket", "product")

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    def get_subtotal(self):
        return self.quantity * self.product.price


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        IN_PROGRESS = "in_progress", "In Progress"
        READY = "ready", "Ready for Collection"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="marketplace_orders")
    delivery_address = models.ForeignKey("accounts.Address", on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    food_miles = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} - {self.customer.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    producer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sold_items")

    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in Order #{self.order.id}"


class Transaction(models.Model):
    class Type(models.TextChoices):
        PAYMENT = "payment", "Payment"
        REFUND = "refund", "Refund"
        COMMISSION = "commission", "Commission"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="transactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")

    transaction_type = models.CharField(max_length=20, choices=Type.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    payment_processor_id = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_type} - £{self.amount} - {self.status}"


class Commission(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="commission_record")
    producer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="commissions")

    order_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Commission on Order #{self.order.id} - £{self.commission_amount}"


class AuditLog(models.Model):
    class Action(models.TextChoices):
        USER_CREATED = "user_created", "User Created"
        USER_UPDATED = "user_updated", "User Updated"
        PRODUCT_CREATED = "product_created", "Product Created"
        PRODUCT_UPDATED = "product_updated", "Product Updated"
        PRODUCT_DELETED = "product_deleted", "Product Deleted"
        ORDER_PLACED = "order_placed", "Order Placed"
        ORDER_CANCELLED = "order_cancelled", "Order Cancelled"
        ORDER_COMPLETED = "order_completed", "Order Completed"
        PAYMENT_PROCESSED = "payment_processed", "Payment Processed"
        INVENTORY_UPDATED = "inventory_updated", "Inventory Updated"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    action = models.CharField(max_length=50, choices=Action.choices)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action} by {self.user} at {self.timestamp}"


class Recipe(models.Model):
    """Recipes created by producers to share with customers."""
    
    class SeasonalTag(models.TextChoices):
        SPRING = "spring", "Spring"
        SUMMER = "summer", "Summer"
        AUTUMN_WINTER = "autumn_winter", "Autumn/Winter"
        ALL_SEASON = "all_season", "All Season"
    
    producer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recipes")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="Brief description or introduction")
    ingredients = models.TextField(help_text="List of ingredients")
    instructions = models.TextField(help_text="Cooking instructions")
    image = models.ImageField(
        upload_to="recipes/",
        blank=True,
        null=True,
        validators=[validate_image_file_extension, validate_image_file_size, validate_image_content_type]
    )
    seasonal_tag = models.CharField(
        max_length=20,
        choices=SeasonalTag.choices,
        default=SeasonalTag.ALL_SEASON
    )
    is_published = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.title} by {self.producer.username}"


class RecipeProduct(models.Model):
    """Links recipes to products from the producer's inventory."""
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="linked_products")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="recipes")
    
    class Meta:
        unique_together = ("recipe", "product")
    
    def __str__(self):
        return f"{self.product.name} in {self.recipe.title}"


class FarmStory(models.Model):
    """Farm stories and educational content shared by producers."""
    producer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="farm_stories")
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="Story content")
    image = models.ImageField(
        upload_to="farm_stories/",
        blank=True,
        null=True,
        validators=[validate_image_file_extension, validate_image_file_size, validate_image_content_type]
    )
    is_published = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Farm Stories"
    
    def __str__(self):
        return f"{self.title} by {self.producer.username}"


class FavoriteRecipe(models.Model):
    """Tracks recipes saved as favorites by customers."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_recipes")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="favorited_by")
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ("user", "recipe")
        ordering = ["-saved_at"]
    
    def __str__(self):
        return f"{self.user.username} saved {self.recipe.title}"


class StockAlert(models.Model):
    """Notifications for low stock levels."""
    
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_alerts")
    producer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stock_alerts")
    
    stock_level = models.PositiveIntegerField(help_text="Stock level when alert was generated")
    threshold = models.PositiveIntegerField(help_text="Threshold that triggered the alert")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"Low Stock Alert: {self.product.name} - {self.stock_level} {self.product.unit} remaining"
    
    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE


class ProductReview(models.Model):
    """Reviews and ratings for products by customers who have purchased them."""
    
    class Rating(models.IntegerChoices):
        ONE_STAR = 1, "1 Star"
        TWO_STARS = 2, "2 Stars"
        THREE_STARS = 3, "3 Stars"
        FOUR_STARS = 4, "4 Stars"
        FIVE_STARS = 5, "5 Stars"
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="product_reviews")
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name="product_reviews", help_text="Order where the product was purchased")
    
    rating = models.IntegerField(choices=Rating.choices)
    title = models.CharField(max_length=200, help_text="Brief review title")
    review_text = models.TextField(help_text="Detailed review")
    is_anonymous = models.BooleanField(default=False, help_text="Hide customer name in public display")
    
    producer_response = models.TextField(blank=True, help_text="Producer's response to the review")
    producer_response_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
        unique_together = ("product", "customer")
        indexes = [
            models.Index(fields=["product", "-created_at"]),
        ]
    
    def __str__(self):
        return f"{self.rating}★ - {self.product.name} by {self.customer.username}"
    
    @property
    def is_verified_purchase(self):
        """Returns True if the review is from a delivered/completed order."""
        from orders.models import Order as OrdersModel
        return self.order.status == OrdersModel.STATUS_DELIVERED
    
    @property
    def display_name(self):
        """Returns the display name for the review author."""
        if self.is_anonymous:
            return "Anonymous"
        return self.customer.get_full_name() or self.customer.username