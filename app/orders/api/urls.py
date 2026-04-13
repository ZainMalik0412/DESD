"""
Orders API URL Configuration
Author: TJ

This file maps URLs to API views using Django REST Framework's router.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CartViewSet, OrderViewSet

# Router automatically creates URL patterns for viewsets
router = DefaultRouter()

# Register viewsets
# This creates URLs like:
# - /cart/ (list/create)
# - /cart/add_item/ (custom action)
# - /cart/update_item/5/ (custom action)
# - /orders/ (list)
# - /orders/5/ (detail)
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
]