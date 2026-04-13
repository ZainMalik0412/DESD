"""
Cart and Order API Serializers
Author: TJ

Serializers convert Django models to/from JSON for API responses.
"""

from rest_framework import serializers
from orders.models import Cart, CartItem, Order, OrderItem
from marketplace.api.serializers import ProductSerializer


class CartItemSerializer(serializers.ModelSerializer):
    """
    Converts CartItem model to JSON.
    
    Example JSON output:
    {
        "id": 1,
        "product": {...product details...},
        "quantity": 2,
        "unit_price": "3.50",
        "line_total": "7.00"
    }
    """
    # Include full product details (name, price, image, etc.)
    product = ProductSerializer(read_only=True)
    
    # For creating/updating, we only need the product ID
    product_id = serializers.IntegerField(write_only=True)
    
    # These are calculated automatically from the model's @property methods
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'unit_price', 'line_total']
        read_only_fields = ['id', 'unit_price', 'line_total']
    
    def validate_quantity(self, value):
        """Ensure quantity is at least 1"""
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        return value


class CartSerializer(serializers.ModelSerializer):
    """
    Converts Cart model to JSON.
    
    Example JSON output:
    {
        "id": 5,
        "status": "active",
        "items": [{...}, {...}],
        "total": "15.50",
        "item_count": 3,
        "created_at": "2026-03-19T10:30:00Z"
    }
    """
    # Include all cart items with full details
    items = CartItemSerializer(many=True, read_only=True)
    
    # Total is calculated from the model's @property method
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    # Custom field: count how many items are in cart
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'status', 'items', 'total', 'item_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'total', 'created_at', 'updated_at']
    
    def get_item_count(self, obj):
        """Count total items in cart"""
        return obj.items.count()


class OrderItemSerializer(serializers.ModelSerializer):
    """Converts OrderItem to JSON"""
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'unit_price', 'quantity', 'line_total']
        read_only_fields = ['id']


class OrderSerializer(serializers.ModelSerializer):
    """
    Converts Order model to JSON.
    
    Shows order history with all items and delivery details.
    """
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'status', 'total', 'commission', 'delivery_date', 'items',
            'full_name', 'email', 'address_line1', 'address_line2',
            'city', 'postcode', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'total', 'commission', 'created_at', 'updated_at']