from django.urls import path
from . import views

urlpatterns = [
    path('', views.browse, name='browse'),
    path('producers/', views.producers, name='producers'),
    path('add-product/', views.add_product, name='add_product'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('product/<int:product_id>/delete/', views.delete_product, name='delete_product'),
]
