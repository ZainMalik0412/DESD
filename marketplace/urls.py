from django.urls import path
from . import views

urlpatterns = [
    path('', views.browse, name='browse'),
    path('producers/', views.producers, name='producers'),
    path('add-product/', views.add_product, name='add_product'),
]
