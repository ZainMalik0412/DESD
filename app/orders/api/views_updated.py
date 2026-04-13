"""
Cart and Order API Views
Author: TJ

These views handle API requests for cart operations.
They use the SAME models as the HTML views, so data is shared.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from orders.models import Cart, CartItem, Order
from marketplace.models import Product
from .serializers import CartSerializer, CartItemSerializer, OrderSerializer


class CartViewSet(viewsets.ModelViewSet):
    """
    API endpoint for shopping cart operations.
    
    Available endpoints:
    - GET /api/cart/ - Get current user's cart
    - POST /api/cart/add_item/ - Add product to cart
    - PATCH /api/cart/update_item/5/ - Update quantity of item #5
    - DELETE /api/cart/remove_item/5/ - Remove item #5
    - POST /api/cart/clear/ - Empty the cart
    
    All endpoints require authentication (user must be logged in).
    """
    
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]  # Must be logged in
    
    def get_queryset(self):
        """
        Only show the current user's active cart.
        This prevents users from seeing other people's carts.
        """
        return Cart.objects.filter(
            user=self.request.user,
            status=Cart.STATUS_ACTIVE
        ).prefetch_related('items__product')  # Optimize database queries
    
    def list(self, request):
        """
        GET /api/cart/
        
        Returns the user's active cart, creating one if it doesn't exist.
        This matches the behavior of the HTML views.
        """
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            status=Cart.STATUS_ACTIVE
        )
        serializer = self.get_serializer(cart)
        return Response(serializer.data)
    
    def create(self, request):
        """
        POST /api/cart/ is not allowed.
        Use POST /api/cart/add_item/ instead.
        """
        return Response(
            {
                'error': 'Direct cart creation is not allowed. Use /api/cart/add_item/ to add products.',
                'hint': 'POST to /api/cart/add_item/ with {"product_id": 1, "quantity": 2}'
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """
        POST /api/cart/add_item/
        
        Add a product to cart or increase quantity if already in cart.
        
        Request body (JSON):
        {
            "product_id": 1,
            "quantity": 2
        }
        
        Response:
        {
            "id": 10,
            "product": {...},
            "quantity": 2,
            "unit_price": "3.50",
            "line_total": "7.00"
        }
        """
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        
        # Validate input
        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create the user's cart (same as HTML views)
        cart, _ = Cart.objects.get_or_create(
            user=request.user,
            status=Cart.STATUS_ACTIVE
        )
        
        # Check if product exists and is available
        product = get_object_or_404(Product, id=product_id, is_available=True)
        
        # Add to cart or update quantity
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            # Item already in cart, add to existing quantity
            cart_item.quantity += int(quantity)
            cart_item.save()
        
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['patch'], url_path='update_item/(?P<item_id>[^/.]+)')
    def update_item(self, request, item_id=None):
        """
        PATCH /api/cart/update_item/5/
        
        Update the quantity of a specific cart item.
        
        Request body:
        {
            "quantity": 3
        }
        """
        cart = get_object_or_404(Cart, user=request.user, status=Cart.STATUS_ACTIVE)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        quantity = request.data.get('quantity')
        if quantity is None:
            return Response(
                {'error': 'quantity is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if int(quantity) < 1:
            return Response(
                {'error': 'quantity must be at least 1'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart_item.quantity = quantity
        cart_item.save()
        
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data)
    
    @action(detail=False, methods=['delete'], url_path='remove_item/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        """
        DELETE /api/cart/remove_item/5/
        
        Remove an item completely from the cart.
        """
        cart = get_object_or_404(Cart, user=request.user, status=Cart.STATUS_ACTIVE)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()
        
        return Response(
            {'message': 'Item removed from cart'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """
        POST /api/cart/clear/
        
        Remove all items from the cart.
        """
        cart = get_object_or_404(Cart, user=request.user, status=Cart.STATUS_ACTIVE)
        cart.items.all().delete()
        
        return Response(
            {'message': 'Cart cleared'},
            status=status.HTTP_200_OK
        )


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing order history.
    
    Available endpoints:
    - GET /api/orders/ - List all user's orders
    - GET /api/orders/5/ - Get details of order #5
    
    Read-only: Orders can only be created through the checkout process.
    """
    
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Only show the current user's orders"""
        return Order.objects.filter(
            user=self.request.user
        ).prefetch_related('items').order_by('-created_at')
