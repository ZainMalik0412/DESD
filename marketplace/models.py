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