"""
API URL routing.
Author: TJ
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router - automatically generates URLs for viewsets
router = DefaultRouter()

# Register viewsets with the router
# This creates:
# - /api/products/ (list)
# - /api/products/{id}/ (detail)
router.register('products', views.ProductViewSet, basename='product')
router.register('categories', views.CategoryViewSet, basename='category')

# URL patterns
urlpatterns = [
    # Include all router URLs
    path('', include(router.urls)),
]