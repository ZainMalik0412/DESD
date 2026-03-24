import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def send_order_confirmation_email(order):
    """Send an email to the customer when an order is placed successfully."""
    subject = f"BRFN - Order #{order.id} Confirmation"

    # Build itemised receipt from order items
    items = order.items.select_related("product").all()
    receipt_lines = []
    for item in items:
        receipt_lines.append(
            f"  {item.product_name} x{item.quantity}  "
            f"@ £{item.unit_price:.2f} each  =  £{item.line_total:.2f}"
        )
    receipt = "\n".join(receipt_lines)

    message = (
        f"Hi {order.full_name},\n\n"
        f"Thank you for your order! Here is your receipt:\n\n"
        f"Order Number: #{order.id}\n"
        f"Date: {order.created_at.strftime('%d %B %Y, %H:%M')}\n\n"
        f"Items Ordered:\n"
        f"{'-' * 50}\n"
        f"{receipt}\n"
        f"{'-' * 50}\n"
        f"Subtotal: £{order.total:.2f}\n"
        f"Commission (5%): £{order.commission:.2f}\n"
        f"Order Total: £{(order.total + order.commission):.2f}\n\n"
        f"Delivery Date: {order.delivery_date}\n"
        f"Delivery Address: {order.address_line1}, {order.city}, {order.postcode}\n\n"
        f"You can view your order status at any time by logging into your account.\n\n"
        f"Kind regards,\n"
        f"The BRFN Team"
    )

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.email],
            fail_silently=True,
        )
        logger.info(f"Order confirmation email sent for Order #{order.id} to {order.email}")
    except Exception as e:
        logger.error(f"Failed to send order confirmation email for Order #{order.id}: {e}")


def send_status_update_email(order, old_status, new_status, note=""):
    """Send an email to the customer when their order status changes."""
    status_display = dict(order.STATUS_CHOICES).get(new_status, new_status)

    subject = f"BRFN - Order #{order.id} Status Update"
    message = (
        f"Hi {order.full_name},\n\n"
        f"Your order #{order.id} has been updated.\n\n"
        f"New Status: {status_display}\n"
    )

    if note:
        message += f"Note from producer: {note}\n"

    message += (
        f"\nYou can view full order details by logging into your account.\n\n"
        f"Kind regards,\n"
        f"The BRFN Team"
    )

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.email],
            fail_silently=True,
        )
        logger.info(f"Status update email sent for Order #{order.id} to {order.email}")
    except Exception as e:
        logger.error(f"Failed to send status update email for Order #{order.id}: {e}")
