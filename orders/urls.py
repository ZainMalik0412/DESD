from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:item_id>/", views.update_cart_item, name="update_cart_item"),
    path("cart/remove/<int:item_id>/", views.remove_cart_item, name="remove_cart_item"),
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/success/", views.stripe_success, name="stripe_success"),
    path("checkout/cancel/", views.stripe_cancel, name="stripe_cancel"),
    path("my-orders/", views.order_list, name="order_list"),
    path("my-orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("my-orders/<int:order_id>/reorder/", views.reorder, name="reorder"),
    path("my-orders/<int:order_id>/receipt/", views.download_receipt, name="download_receipt"),
    path("manage/", views.manage_orders, name="manage_orders"),
    path("manage/<int:order_id>/", views.manage_order_detail, name="manage_order_detail"),
    path("stock-alerts/", views.stock_alerts, name="stock_alerts"),
    path("payments/", views.payments, name="payments"),
    path("payments/report/csv/", views.payments_report_csv, name="payments_report_csv"),
]