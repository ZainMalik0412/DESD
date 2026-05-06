import logging
import re

from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def sanitize_email_content(text):
    """
    Sanitize text to prevent email header injection.
    Removes newlines and carriage returns that could be used to inject headers.
    """
    if not text:
        return ""
    # Remove any newline characters that could break email headers
    return re.sub(r'[\r\n]+', ' ', str(text).strip())


def _resolve_recipients(order):
    """
    Build the list of email addresses that should receive an order email.

    The signup email (order.user.email) is the canonical, verified address
    captured at registration — it's the address the customer expects receipts
    at. We send there first.

    If the customer typed a different (still valid) email into the checkout
    form, we add it as a secondary recipient so they can also receive the
    receipt at their preferred address. Duplicates and invalid entries are
    dropped.
    """
    candidates = []

    user = getattr(order, "user", None)
    signup_email = getattr(user, "email", None) if user else None
    if signup_email:
        candidates.append(signup_email)

    form_email = getattr(order, "email", None)
    if form_email:
        candidates.append(form_email)

    seen = set()
    recipients = []
    for raw in candidates:
        email = sanitize_email_content(raw).lower()
        if not email or email in seen:
            continue
        try:
            validate_email(email)
        except ValidationError:
            logger.warning(
                "Skipping invalid email address %r when notifying order #%s",
                raw,
                getattr(order, "id", "?"),
            )
            continue
        seen.add(email)
        recipients.append(email)

    return recipients


def send_order_confirmation_email(order):
    """Send an email to the customer when an order is placed successfully.

    The receipt always goes to the email address the customer signed up with
    (``order.user.email``), and additionally to the checkout-form email if
    that differs. This guarantees the customer receives the receipt at their
    canonical inbox even if they typed a different address at checkout.
    """
    full_name = sanitize_email_content(order.full_name)
    address_line1 = sanitize_email_content(order.address_line1)
    city = sanitize_email_content(order.city)
    postcode = sanitize_email_content(order.postcode)

    recipients = _resolve_recipients(order)
    if not recipients:
        logger.error(
            "Cannot send order confirmation for Order #%s: no valid recipient email "
            "(user.email=%r, order.email=%r)",
            getattr(order, "id", "?"),
            getattr(getattr(order, "user", None), "email", None),
            getattr(order, "email", None),
        )
        return False

    subject = f"BRFN - Order #{order.id} Confirmation"

    items = order.items.select_related("product").all()
    receipt_lines = []
    for item in items:
        product_name = sanitize_email_content(item.product_name)
        receipt_lines.append(
            f"  {product_name} x{item.quantity}  "
            f"@ £{item.unit_price:.2f} each  =  £{item.line_total:.2f}"
        )
    receipt = "\n".join(receipt_lines)

    message = (
        f"Hi {full_name},\n\n"
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
        f"Delivery Address: {address_line1}, {city}, {postcode}\n\n"
        f"You can view your order status at any time by logging into your account.\n\n"
        f"Kind regards,\n"
        f"The BRFN Team"
    )

    try:
        sent = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=True,
        )
        if sent:
            logger.info(
                "Order confirmation email sent for Order #%s to %s",
                order.id,
                ", ".join(recipients),
            )
        else:
            logger.warning(
                "send_mail returned 0 for Order #%s confirmation (recipients=%s) — "
                "check EMAIL_BACKEND / SMTP credentials",
                order.id,
                ", ".join(recipients),
            )
        return bool(sent)
    except Exception as e:
        logger.error(
            "Failed to send order confirmation email for Order #%s: %s",
            order.id,
            e,
        )
        return False


def send_status_update_email(order, old_status, new_status, note=""):
    """Send an email to the customer when their order status changes."""
    full_name = sanitize_email_content(order.full_name)
    note = sanitize_email_content(note)

    recipients = _resolve_recipients(order)
    if not recipients:
        logger.error(
            "Cannot send status update for Order #%s: no valid recipient email",
            getattr(order, "id", "?"),
        )
        return False

    status_display = dict(order.STATUS_CHOICES).get(new_status, new_status)

    subject = f"BRFN - Order #{order.id} Status Update"
    message = (
        f"Hi {full_name},\n\n"
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
        sent = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=True,
        )
        if sent:
            logger.info(
                "Status update email sent for Order #%s to %s",
                order.id,
                ", ".join(recipients),
            )
        else:
            logger.warning(
                "send_mail returned 0 for Order #%s status update (recipients=%s) — "
                "check EMAIL_BACKEND / SMTP credentials",
                order.id,
                ", ".join(recipients),
            )
        return bool(sent)
    except Exception as e:
        logger.error(
            "Failed to send status update email for Order #%s: %s",
            order.id,
            e,
        )
        return False
