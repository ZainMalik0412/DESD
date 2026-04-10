from django.contrib import admin
from .models import (
    Category, Product, Basket, BasketItem, 
    Order, OrderItem, Transaction, Commission, AuditLog,
    Recipe, RecipeProduct, FarmStory, FavoriteRecipe, ProductReview
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "producer", "category", "price", "unit", "stock_quantity", "is_available")
    list_filter = ("is_available", "category", "unit")
    search_fields = ("name", "description", "producer__username")


@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "updated_at")
    search_fields = ("user__username",)


class BasketItemInline(admin.TabularInline):
    model = BasketItem
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "producer", "quantity", "unit_price", "subtotal")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "total_amount", "food_miles", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("customer__username", "id")
    inlines = [OrderItemInline]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "transaction_type", "amount", "status", "created_at")
    list_filter = ("transaction_type", "status", "created_at")
    search_fields = ("user__username", "payment_processor_id")


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ("order", "producer", "order_amount", "commission_rate", "commission_amount", "created_at")
    list_filter = ("created_at",)
    search_fields = ("producer__username", "order__id")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "model_name", "object_id", "timestamp", "ip_address")
    list_filter = ("action", "model_name", "timestamp")
    search_fields = ("user__username", "model_name", "object_id")
    readonly_fields = ("user", "action", "model_name", "object_id", "details", "ip_address", "timestamp")


class RecipeProductInline(admin.TabularInline):
    model = RecipeProduct
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("title", "producer", "seasonal_tag", "is_published", "created_at")
    list_filter = ("is_published", "seasonal_tag", "created_at")
    search_fields = ("title", "producer__username", "ingredients", "instructions")
    inlines = [RecipeProductInline]


@admin.register(FarmStory)
class FarmStoryAdmin(admin.ModelAdmin):
    list_display = ("title", "producer", "is_published", "created_at")
    list_filter = ("is_published", "created_at")
    search_fields = ("title", "producer__username", "content")


@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe", "saved_at")
    list_filter = ("saved_at",)
    search_fields = ("user__username", "recipe__title")


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "customer", "rating", "title", "created_at", "is_anonymous")
    list_filter = ("rating", "is_anonymous", "created_at")
    search_fields = ("product__name", "customer__username", "title", "review_text")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Review Information", {
            "fields": ("product", "customer", "order", "rating", "title", "review_text", "is_anonymous")
        }),
        ("Producer Response", {
            "fields": ("producer_response", "producer_response_date"),
            "classes": ("collapse",)
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )