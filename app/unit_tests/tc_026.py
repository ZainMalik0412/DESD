"""
Test Case ID: TC-026

Verifies that order receipt emails are reliably delivered to the address
the customer signed up with, regardless of what was typed into the
checkout form. Also covers status-update emails and edge cases like
missing/invalid emails so we never silently lose a notification again.

Django substitutes the email backend with an in-memory backend during
tests, so ``django.core.mail.outbox`` captures every send_mail() call.
"""

from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail

from marketplace.models import Product, Category
from orders.models import Cart, Order, OrderItem
from orders.notifications import (
    send_order_confirmation_email,
    send_status_update_email,
)


CustomUser = get_user_model()


class TC026OrderConfirmationEmailTests(TestCase):
    """End-to-end and unit-level tests for order receipt emails."""

    def setUp(self):
        self.client = Client()

        self.producer = CustomUser.objects.create_user(
            username='tc026_producer', email='producer@test.com',
            password='Password123!', role=CustomUser.Role.PRODUCER,
            first_name='Bristol', last_name='Farm',
        )

        # The customer's CANONICAL signup email — every receipt must reach it.
        self.signup_email = 'jane.signup@test.com'
        self.customer = CustomUser.objects.create_user(
            username='tc026_customer', email=self.signup_email,
            password='Password123!', role=CustomUser.Role.CUSTOMER,
            first_name='Jane', last_name='Buyer',
            delivery_address='5 Market St', postcode='BS1 1AA',
        )

        self.category = Category.objects.create(name='Produce', slug='produce-tc026')
        self.product_a = Product.objects.create(
            producer=self.producer, category=self.category,
            name='Organic Carrots', price=Decimal('2.00'), stock_quantity=50,
        )
        self.product_b = Product.objects.create(
            producer=self.producer, category=self.category,
            name='Farm Eggs', price=Decimal('3.50'), stock_quantity=50,
        )

        self.delivery_date = (date.today() + timedelta(days=3)).strftime('%Y-%m-%d')

    def _build_paid_order(self, form_email=None):
        """Drive the full checkout → Stripe success flow and return the Order."""
        if form_email is None:
            form_email = self.signup_email

        self.client.login(username='tc026_customer', password='Password123!')
        self.client.post(
            reverse('orders:add_to_cart', args=[self.product_a.id]),
            {'quantity': '2'}, HTTP_REFERER='/browse/',
        )
        self.client.post(
            reverse('orders:add_to_cart', args=[self.product_b.id]),
            {'quantity': '1'}, HTTP_REFERER='/browse/',
        )

        with patch('stripe.checkout.Session.create') as mock_create, \
             patch('stripe.checkout.Session.retrieve') as mock_retrieve:
            mock_session = MagicMock()
            mock_session.url = 'https://checkout.stripe.com/test'
            mock_session.id = 'cs_test_tc026'
            mock_session.payment_status = 'paid'
            mock_create.return_value = mock_session
            mock_retrieve.return_value = mock_session

            self.client.post(reverse('orders:checkout'), {
                'full_name': 'Jane Buyer', 'email': form_email,
                'address_line1': '5 Market St', 'address_line2': '',
                'city': 'Bristol', 'postcode': 'BS1 1AA',
                'delivery_date': self.delivery_date,
            })
            self.client.get(
                reverse('orders:stripe_success') + '?session_id=cs_test_tc026'
            )

        return Order.objects.get(user=self.customer)

    # ------------------------------------------------------------------ #
    # End-to-end: an actual checkout produces an actual email.           #
    # ------------------------------------------------------------------ #

    def test_email_sent_after_successful_checkout(self):
        """A confirmation email is created in the outbox after a paid order."""
        mail.outbox = []
        order = self._build_paid_order()

        self.assertEqual(
            len(mail.outbox), 1,
            "Exactly one confirmation email should be sent after checkout",
        )
        sent = mail.outbox[0]
        self.assertIn(self.signup_email, sent.to,
                      "Receipt must be delivered to the signup email")
        self.assertIn(f"#{order.id}", sent.subject,
                      "Subject should include the order number")
        self.assertIn("Confirmation", sent.subject)

    def test_email_recipient_is_always_the_signup_email(self):
        """Even if the form email differs from signup, signup email is included."""
        mail.outbox = []
        different_form_email = 'jane.shipping@test.com'
        self._build_paid_order(form_email=different_form_email)

        self.assertEqual(len(mail.outbox), 1)
        recipients = [r.lower() for r in mail.outbox[0].to]

        self.assertIn(
            self.signup_email.lower(), recipients,
            "Signup email must always be a recipient — that's the user's "
            "expectation for 'send to the email I signed up with'",
        )
        self.assertIn(
            different_form_email.lower(), recipients,
            "If a different email was given at checkout, it should also be "
            "included as a secondary recipient",
        )

    def test_email_not_duplicated_when_form_matches_signup(self):
        """When form email == signup email, only one address is in To:."""
        mail.outbox = []
        self._build_paid_order(form_email=self.signup_email)

        self.assertEqual(len(mail.outbox), 1)
        recipients = [r.lower() for r in mail.outbox[0].to]
        self.assertEqual(recipients.count(self.signup_email.lower()), 1)
        self.assertEqual(len(recipients), 1)

    def test_email_body_contains_receipt_details(self):
        """The receipt body lists the items, totals, and delivery info."""
        mail.outbox = []
        order = self._build_paid_order()

        body = mail.outbox[0].body
        self.assertIn('Organic Carrots', body)
        self.assertIn('Farm Eggs', body)
        self.assertIn(f"Order Number: #{order.id}", body)
        self.assertIn('Subtotal:', body)
        self.assertIn('Commission (5%):', body)
        self.assertIn('Order Total:', body)
        self.assertIn(f"£{order.total:.2f}", body)
        self.assertIn('5 Market St', body)
        self.assertIn('BS1 1AA', body)

    def test_email_from_address_is_default(self):
        """The From: address is the configured DEFAULT_FROM_EMAIL."""
        from django.conf import settings
        mail.outbox = []
        self._build_paid_order()

        self.assertEqual(mail.outbox[0].from_email, settings.DEFAULT_FROM_EMAIL)

    # ------------------------------------------------------------------ #
    # Unit-level: call the helper directly with edge-case inputs.        #
    # ------------------------------------------------------------------ #

    def _make_order(self, form_email='', user_email_override=None):
        """Build a saved Order without going through Stripe."""
        if user_email_override is not None:
            self.customer.email = user_email_override
            self.customer.save(update_fields=['email'])

        order = Order.objects.create(
            user=self.customer,
            full_name='Jane Buyer',
            email=form_email,
            address_line1='5 Market St',
            city='Bristol',
            postcode='BS1 1AA',
            total=Decimal('7.50'),
            commission=Decimal('0.38'),
            delivery_date=date.today() + timedelta(days=3),
            status=Order.STATUS_CONFIRMED,
        )
        OrderItem.objects.create(
            order=order, product=self.product_a,
            product_name='Organic Carrots',
            unit_price=Decimal('2.00'), quantity=2,
            line_total=Decimal('4.00'),
        )
        return order

    def test_falls_back_to_signup_email_when_form_email_blank(self):
        """If checkout email is blank, signup email still receives the receipt."""
        mail.outbox = []
        order = self._make_order(form_email='')

        result = send_order_confirmation_email(order)

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            [r.lower() for r in mail.outbox[0].to],
            [self.signup_email.lower()],
        )

    def test_invalid_form_email_is_skipped_signup_still_used(self):
        """A garbage form email is dropped; the signup email still gets it."""
        mail.outbox = []
        order = self._make_order(form_email='not-an-email-at-all')

        result = send_order_confirmation_email(order)

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        recipients = [r.lower() for r in mail.outbox[0].to]
        self.assertIn(self.signup_email.lower(), recipients)
        self.assertNotIn('not-an-email-at-all', recipients)

    def test_returns_false_when_no_valid_recipient_exists(self):
        """No signup email AND no valid form email → no send, returns False."""
        mail.outbox = []
        order = self._make_order(form_email='', user_email_override='')

        result = send_order_confirmation_email(order)

        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_header_injection_attempt_is_neutralised(self):
        """A malicious full_name with newlines must not inject headers."""
        mail.outbox = []
        order = self._make_order(form_email=self.signup_email)
        order.full_name = "Attacker\r\nBcc: leaker@evil.com"
        order.save(update_fields=['full_name'])

        send_order_confirmation_email(order)

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, [self.signup_email.lower()])
        self.assertNotIn('leaker@evil.com', sent.to)
        self.assertNotIn('\n', sent.body.split('\n')[0])

    # ------------------------------------------------------------------ #
    # Status update email behaves the same way.                          #
    # ------------------------------------------------------------------ #

    def test_status_update_email_goes_to_signup_email(self):
        """Producer status changes also email the signup address."""
        mail.outbox = []
        order = self._make_order(form_email=self.signup_email)

        result = send_status_update_email(
            order,
            old_status=Order.STATUS_CONFIRMED,
            new_status=Order.STATUS_READY,
            note="Ready for collection",
        )

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn(self.signup_email.lower(), [r.lower() for r in sent.to])
        self.assertIn('Status Update', sent.subject)
        self.assertIn('Ready', sent.body)
        self.assertIn('Ready for collection', sent.body)

    # ------------------------------------------------------------------ #
    # Regression guards: existing checkout behaviour still works.        #
    # ------------------------------------------------------------------ #

    def test_email_failure_does_not_break_order_creation(self):
        """If the email backend raises, the order is still saved and visible."""
        mail.outbox = []

        with patch('orders.notifications.send_mail', side_effect=Exception("SMTP down")):
            order = self._build_paid_order()

        self.assertIsNotNone(order.id)
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)
        self.assertEqual(
            Cart.objects.filter(user=self.customer, status=Cart.STATUS_ACTIVE).exists(),
            False,
            "Cart should still convert even if the receipt email fails",
        )

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_works_with_locmem_backend_explicitly(self):
        """Sanity check: behaviour holds with the in-memory backend."""
        mail.outbox = []
        order = self._make_order(form_email=self.signup_email)

        send_order_confirmation_email(order)

        self.assertEqual(len(mail.outbox), 1)
