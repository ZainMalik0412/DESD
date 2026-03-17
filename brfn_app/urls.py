from django.contrib import admin
from django.urls import path, include
from brfn_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('browse/', include('marketplace.urls')),
    path('accounts/', include('accounts.urls')),
    path("orders/", include("orders.urls")),
    path("terms/", views.terms, name="terms"),
]
