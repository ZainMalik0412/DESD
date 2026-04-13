from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from marketplace.models import Product, Category
from orders.models import Cart, CartItem, Order, OrderItem


CustomUser = get_user_model()


class TC007SingleProducerCheckoutTests(TestCase):
    """
    Test Case ID: TC-007
    """

    def setUp(self):
        self.client = Client()

        self.producer = CustomUser.objects.create_user(
            username='bristol_valley_farm', email='bvf@test.com', password='Password123!',
            role=CustomUser.Role.PRODUCER, first_name='Bristol', last_name='Farm'
        )
        self.customer = CustomUser.objects.create_user(
            username='customer_tc07', email='c@test.com', password='Password123!',
            role=CustomUser.Role.CUSTOMER, first_name='Jane', last_name='Buyer',
            delivery_address='5 Market St', postcode='BS1 1AA'
        )

        self.category = Category.objects.create(name='Produce', slug='produce')
        self.product_a = Product.objects.create(
            producer=self.producer, category=self.category,
            name='Organic Carrots', price=Decimal('2.00'), stock_quantity=50
        )
        self.product_b = Product.objects.create(
            producer=self.producer, category=self.category,
            name='Farm Eggs', price=Decimal('3.50'), stock_quantity=50
        )

        self.delivery_date = (date.today() + timedelta(days=3)).strftime('%Y-%m-%d')

    def _add_products_and_login(self):
        """Helper: log in as customer and add both products to cart."""
        self.client.login(username='customer_tc07', password='Password123!')
        self.client.post(reverse('orders:add_to_cart', args=[self.product_a.id]), {'quantity': '2'}, HTTP_REFERER='/browse/')
        self.client.post(reverse('orders:add_to_cart', args=[self.product_b.id]), {'quantity': '1'}, HTTP_REFERER='/browse/')

    def test_cart_confirms_single_producer(self):
        """Cart view shows items from only one producer."""
        self._add_products_and_login()

        response = self.client.get(reverse('orders:cart'))
        self.assertEqual(response.status_code, 200)

        grouped = response.context['grouped_items']
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]['producer'].username, 'bristol_valley_farm')
        self.assertEqual(len(grouped[0]['items']), 2)

    def test_checkout_prefills_delivery_address(self):
        """Checkout page pre-fills the customer's delivery address."""
        self._add_products_and_login()

        response = self.client.get(reverse('orders:checkout'))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        self.assertIn('5 Market St', content)
        self.assertIn('BS1 1AA', content)

    def test_checkout_shows_producer_details_and_commission(self):
        """Checkout summary shows producer section, subtotal, and 5% commission."""
        self._add_products_and_login()

        response = self.client.get(reverse('orders:checkout'))
        grouped = response.context['grouped_items']

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]['subtotal'], Decimal('7.50'))

        self.assertEqual(response.context['commission'], Decimal('0.38'))
        self.assertEqual(response.context['grand_total'], Decimal('7.88'))
        self.assertContains(response, 'Network Commission (5%)')

    def test_checkout_enforces_48h_lead_time(self):
        """Delivery date less than 48 hours from now is rejected."""
        self._add_products_and_login()

        bad_date = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        self.client.post(reverse('orders:checkout'), {
            'full_name': 'Jane Buyer', 'email': 'c@test.com',
            'address_line1': '5 Market St', 'city': 'Bristol', 'postcode': 'BS1 1AA',
            'delivery_date': bad_date,
        })
        self.assertTrue(Cart.objects.filter(user=self.customer, status=Cart.STATUS_ACTIVE).exists())
        self.assertEqual(Order.objects.filter(user=self.customer).count(), 0)

    @patch('stripe.checkout.Session.create')
    @patch('stripe.checkout.Session.retrieve')
    def test_order_created_with_pending_status_and_commission(self, mock_retrieve, mock_create):
        """Placing order creates it with Pending status, correct total and commission."""
        # Mock Stripe responses
        mock_session = MagicMock()
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_session.id = 'cs_test_123'
        mock_session.payment_status = 'paid'
        mock_create.return_value = mock_session
        mock_retrieve.return_value = mock_session
        
        self._add_products_and_login()

        # Post to checkout (redirects to Stripe)
        response = self.client.post(reverse('orders:checkout'), {
            'full_name': 'Jane Buyer', 'email': 'c@test.com',
            'address_line1': '5 Market St', 'address_line2': '',
            'city': 'Bristol', 'postcode': 'BS1 1AA',
            'delivery_date': self.delivery_date,
        })
        
        # Simulate successful Stripe payment
        response = self.client.get(reverse('orders:stripe_success') + '?session_id=cs_test_123')

        self.assertEqual(Order.objects.filter(user=self.customer).count(), 1)
        order = Order.objects.get(user=self.customer)

        self.assertEqual(order.status, Order.STATUS_CONFIRMED)
        self.assertEqual(order.total, Decimal('7.50'))
        self.assertEqual(order.commission, Decimal('0.38'))
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.full_name, 'Jane Buyer')
        self.assertIsNotNone(order.delivery_date)

    @patch('stripe.checkout.Session.create')
    @patch('stripe.checkout.Session.retrieve')
    def test_customer_can_view_order(self, mock_retrieve, mock_create):
        """Customer can see the completed order with all details."""
        # Mock Stripe responses
        mock_session = MagicMock()
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_session.id = 'cs_test_123'
        mock_session.payment_status = 'paid'
        mock_create.return_value = mock_session
        mock_retrieve.return_value = mock_session
        
        self._add_products_and_login()

        self.client.post(reverse('orders:checkout'), {
            'full_name': 'Jane Buyer', 'email': 'c@test.com',
            'address_line1': '5 Market St', 'address_line2': '',
            'city': 'Bristol', 'postcode': 'BS1 1AA',
            'delivery_date': self.delivery_date,
        })
        
        # Complete payment
        self.client.get(reverse('orders:stripe_success') + '?session_id=cs_test_123')
        order = Order.objects.get(user=self.customer)

        response = self.client.get(reverse('orders:order_detail', args=[order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Organic Carrots')
        self.assertContains(response, 'Farm Eggs')
        self.assertContains(response, 'bristol_valley_farm')

    @patch('stripe.checkout.Session.create')
    @patch('stripe.checkout.Session.retrieve')
    def test_producer_can_view_order(self, mock_retrieve, mock_create):
        """Producer can see their order items from this single-producer order."""
        # Mock Stripe responses
        mock_session = MagicMock()
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_session.id = 'cs_test_123'
        mock_session.payment_status = 'paid'
        mock_create.return_value = mock_session
        mock_retrieve.return_value = mock_session
        
        self._add_products_and_login()

        self.client.post(reverse('orders:checkout'), {
            'full_name': 'Jane Buyer', 'email': 'c@test.com',
            'address_line1': '5 Market St', 'address_line2': '',
            'city': 'Bristol', 'postcode': 'BS1 1AA',
            'delivery_date': self.delivery_date,
        })
        
        # Complete payment
        self.client.get(reverse('orders:stripe_success') + '?session_id=cs_test_123')
        order = Order.objects.get(user=self.customer)

        self.client.logout()
        self.client.login(username='bristol_valley_farm', password='Password123!')

        response = self.client.get(reverse('orders:manage_order_detail', args=[order.id]))
        self.assertEqual(response.status_code, 200)

        items = list(response.context['items'])
        self.assertEqual(len(items), 2)
        self.assertContains(response, 'Jane Buyer')
        self.assertContains(response, '5 Market St')
