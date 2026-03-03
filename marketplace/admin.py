from django.contrib import admin
from .models import (
    Category, Product, Basket, BasketItem, 
    Order, OrderItem, Transaction, Commission, AuditLog
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