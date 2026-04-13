"""
API Serializers - Convert models to JSON and validate API input.
Author: TJ
"""

from rest_framework import serializers
from marketplace.models import Product, Category


class CategorySerializer(serializers.ModelSerializer):
    """
    Converts Category model to JSON.
    
    Example output:
    {
        "id": 1,
        "name": "Vegetables",
        "slug": "vegetables",
        "description": "Fresh local vegetables"
    }
    """
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description']


class ProductSerializer(serializers.ModelSerializer):
    """
    Converts Product model to JSON.
    
    Adds extra fields:
    - producer_name: Username of the producer
    - category_name: Name of the category
    
    Example output:
    {
        "id": 1,
        "name": "Organic Tomatoes",
        "description": "Fresh from the farm",
        "price": "2.50",
        "unit": "kg",
        "stock_quantity": 50,
        "is_available": true,
        "category": 1,
        "category_name": "Vegetables",
        "producer": 2,
        "producer_name": "farmer_john",
        "created_at": "2026-03-10T10:00:00Z",
        "updated_at": "2026-03-10T10:00:00Z"
    }
    """
    
    # Extra fields that aren't in the model
    producer_name = serializers.CharField(source='producer.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'unit',
            'stock_quantity', 'is_available', 'category', 'category_name',
            'producer', 'producer_name', 'created_at', 'updated_at'
        ]
        # These fields can't be changed via API
        read_only_fields = ['producer', 'created_at', 'updated_at']