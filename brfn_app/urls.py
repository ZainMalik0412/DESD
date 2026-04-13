from django.contrib import admin
from django.urls import path, include
from brfn_app import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('browse/', include('marketplace.urls')),
    path('accounts/', include('accounts.urls')),
    path("orders/", include("orders.urls")),
    path("terms/", views.terms, name="terms"),
    path("health/", views.health, name="health"),
    path('api/', include('marketplace.api.urls')),  # Products/Categories API
    path('api/', include('orders.api.urls')),        # Cart/Orders API
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)