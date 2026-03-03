from django.conf import settings
from django.db import models


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

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    producer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products")

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.ITEM)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("producer", "name")

    def __str__(self):
        return f"{self.name} - {self.producer.username}"


class Basket(models.Model):
    """Shopping basket for customers."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="basket")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Basket for {self.user.username}"

    def get_total(self):
        return sum(item.get_subtotal() for item in self.items.all())


class BasketItem(models.Model):
    """Individual items in a basket."""
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
    """Customer orders."""
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        IN_PROGRESS = "in_progress", "In Progress"
        READY = "ready", "Ready for Collection"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="marketplace_orders")
    delivery_address = models.ForeignKey('accounts.Address', on_delete=models.SET_NULL, null=True, blank=True)
    
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
    """Individual items within an order."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    producer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sold_items")
    
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in Order #{self.order.id}"


class Transaction(models.Model):
    """Financial transactions for order payments."""
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
    """Commission records for platform earnings."""
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="commission_record")
    producer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="commissions")
    
    order_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)  # Percentage
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Commission on Order #{self.order.id} - £{self.commission_amount}"


class AuditLog(models.Model):
    """Audit trail for important system actions."""
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
