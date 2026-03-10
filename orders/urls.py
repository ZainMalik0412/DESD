from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:item_id>/", views.update_cart_item, name="update_cart_item"),
    path("cart/remove/<int:item_id>/", views.remove_cart_item, name="remove_cart_item"),
    path("checkout/", views.checkout, name="checkout"),
    path("my-orders/", views.order_list, name="order_list"),
    path("my-orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("manage/", views.manage_orders, name="manage_orders"),
    path("manage/<int:order_id>/", views.manage_order_detail, name="manage_order_detail"),
]