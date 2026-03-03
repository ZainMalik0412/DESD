from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Address


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_staff", "is_superuser")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")

    fieldsets = UserAdmin.fieldsets + (
        ("Role", {"fields": ("role",)}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Role", {"fields": ("role",)}),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "postcode", "is_default", "created_at")
    list_filter = ("is_default", "city")
    search_fields = ("user__username", "address_line1", "city", "postcode")