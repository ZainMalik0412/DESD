from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from marketplace.models import Product, Category
from orders.models import Cart, CartItem, Order, OrderItem


CustomUser = get_user_model()


class TC008MultiVendorCheckoutTests(TestCase):
    """
    Test Case ID: TC-008
    """

    def setUp(self):
        self.client = Client()

        self.producer1 = CustomUser.objects.create_user(
            username='bristol_valley_farm', email='bvf@test.com', password='Password123!',
            role=CustomUser.Role.PRODUCER, first_name='Bristol', last_name='Farm'
        )
        self.producer2 = CustomUser.objects.create_user(
            username='hillside_dairy', email='hd@test.com', password='Password123!',
            role=CustomUser.Role.PRODUCER, first_name='Hillside', last_name='Dairy'
        )

        self.customer = CustomUser.objects.create_user(
            username='customer_tc08', email='c@test.com', password='Password123!',
            role=CustomUser.Role.CUSTOMER, first_name='Jane', last_name='Buyer',
            delivery_address='5 Market St', postcode='BS1 1AA'
        )

        self.category = Category.objects.create(name='Mixed', slug='mixed')

        self.p1_prod_a = Product.objects.create(
            producer=self.producer1, category=self.category,
            name='Organic Carrots', price=Decimal('2.00'), stock_quantity=50
        )
        self.p1_prod_b = Product.objects.create(
            producer=self.producer1, category=self.category,
            name='Farm Eggs', price=Decimal('3.50'), stock_quantity=50
        )

        self.p2_prod_a = Product.objects.create(
            producer=self.producer2, category=self.category,
            name='Fresh Milk', price=Decimal('1.50'), stock_quantity=50
        )
        self.p2_prod_b = Product.objects.create(
            producer=self.producer2, category=self.category,
            name='Cheddar Cheese', price=Decimal('4.00'), stock_quantity=50
        )

    def _add_all_to_cart(self):
        """Helper: add 2 items from each producer to cart."""
        self.client.login(username='customer_tc08', password='Password123!')
        self.client.post(reverse('orders:add_to_cart', args=[self.p1_prod_a.id]), {'quantity': '2'}, HTTP_REFERER='/browse/')
        self.client.post(reverse('orders:add_to_cart', args=[self.p1_prod_b.id]), {'quantity': '1'}, HTTP_REFERER='/browse/')
        self.client.post(reverse('orders:add_to_cart', args=[self.p2_prod_a.id]), {'quantity': '3'}, HTTP_REFERER='/browse/')
        self.client.post(reverse('orders:add_to_cart', args=[self.p2_prod_b.id]), {'quantity': '1'}, HTTP_REFERER='/browse/')

    def test_cart_groups_by_producer(self):
        """Cart view groups items by producer with per-producer subtotals."""
        self._add_all_to_cart()

        response = self.client.get(reverse('orders:cart'))
        self.assertEqual(response.status_code, 200)

        grouped = response.context['grouped_items']
        self.assertEqual(len(grouped), 2)

        producer_names = [g['producer'].username for g in grouped]
        self.assertIn('bristol_valley_farm', producer_names)
        self.assertIn('hillside_dairy', producer_names)

        for group in grouped:
            if group['producer'].username == 'bristol_valley_farm':
                self.assertEqual(group['subtotal'], Decimal('7.50'))
            elif group['producer'].username == 'hillside_dairy':
                self.assertEqual(group['subtotal'], Decimal('8.50'))

    def test_checkout_shows_commission_and_grouped(self):
        """Checkout summary shows producer grouping, commission, and grand total."""
        self._add_all_to_cart()

        response = self.client.get(reverse('orders:checkout'))
        self.assertEqual(response.status_code, 200)

        grouped = response.context['grouped_items']
        self.assertEqual(len(grouped), 2)

        self.assertEqual(response.context['commission'], Decimal('0.80'))
        self.assertEqual(response.context['grand_total'], Decimal('16.80'))

        self.assertContains(response, 'Network Commission (5%)')

    @patch('stripe.checkout.Session.create')
    @patch('stripe.checkout.Session.retrieve')
    def test_multi_vendor_order_created_with_commission(self, mock_retrieve, mock_create):
        """Placing a multi-vendor order creates one Order with correct commission."""
        # Mock Stripe responses
        mock_session = MagicMock()
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_session.id = 'cs_test_123'
        mock_session.payment_status = 'paid'
        mock_create.return_value = mock_session
        mock_retrieve.return_value = mock_session
        
        self._add_all_to_cart()

        delivery_date = (date.today() + timedelta(days=3)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('orders:checkout'), {
            'full_name': 'Jane Buyer', 'email': 'c@test.com',
            'address_line1': '5 Market St', 'address_line2': '',
            'city': 'Bristol', 'postcode': 'BS1 1AA',
            'delivery_date': delivery_date,
        })
        
        # Complete payment
        self.client.get(reverse('orders:stripe_success') + '?session_id=cs_test_123')

        self.assertEqual(Order.objects.filter(user=self.customer).count(), 1)
        order = Order.objects.get(user=self.customer)

        self.assertEqual(order.total, Decimal('16.00'))
        self.assertEqual(order.commission, Decimal('0.80'))

        self.assertEqual(order.items.count(), 4)

    @patch('stripe.checkout.Session.create')
    @patch('stripe.checkout.Session.retrieve')
    def test_producer1_sees_only_their_items(self, mock_retrieve, mock_create):
        """Producer 1 can only see their 2 items in the multi-vendor order."""
        # Mock Stripe responses
        mock_session = MagicMock()
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_session.id = 'cs_test_123'
        mock_session.payment_status = 'paid'
        mock_create.return_value = mock_session
        mock_retrieve.return_value = mock_session
        
        self._add_all_to_cart()

        delivery_date = (date.today() + timedelta(days=3)).strftime('%Y-%m-%d')
        self.client.post(reverse('orders:checkout'), {
            'full_name': 'Jane Buyer', 'email': 'c@test.com',
            'address_line1': '5 Market St', 'address_line2': '',
            'city': 'Bristol', 'postcode': 'BS1 1AA',
            'delivery_date': delivery_date,
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
        item_names = {i.product_name for i in items}
        self.assertEqual(item_names, {'Organic Carrots', 'Farm Eggs'})

    @patch('stripe.checkout.Session.create')
    @patch('stripe.checkout.Session.retrieve')
    def test_producer2_sees_only_their_items(self, mock_retrieve, mock_create):
        """Producer 2 can only see their 2 items in the multi-vendor order."""
        # Mock Stripe responses
        mock_session = MagicMock()
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_session.id = 'cs_test_123'
        mock_session.payment_status = 'paid'
        mock_create.return_value = mock_session
        mock_retrieve.return_value = mock_session
        
        self._add_all_to_cart()

        delivery_date = (date.today() + timedelta(days=3)).strftime('%Y-%m-%d')
        self.client.post(reverse('orders:checkout'), {
            'full_name': 'Jane Buyer', 'email': 'c@test.com',
            'address_line1': '5 Market St', 'address_line2': '',
            'city': 'Bristol', 'postcode': 'BS1 1AA',
            'delivery_date': delivery_date,
        })
        
        # Complete payment
        self.client.get(reverse('orders:stripe_success') + '?session_id=cs_test_123')
        order = Order.objects.get(user=self.customer)

        self.client.logout()
        self.client.login(username='hillside_dairy', password='Password123!')

        response = self.client.get(reverse('orders:manage_order_detail', args=[order.id]))
        self.assertEqual(response.status_code, 200)

        items = list(response.context['items'])
        self.assertEqual(len(items), 2)
        item_names = {i.product_name for i in items}
        self.assertEqual(item_names, {'Fresh Milk', 'Cheddar Cheese'})

    @patch('stripe.checkout.Session.create')
    @patch('stripe.checkout.Session.retrieve')
    def test_customer_order_detail_grouped_by_producer(self, mock_retrieve, mock_create):
        """Customer order detail shows items grouped by producer with subtotals."""
        # Mock Stripe responses
        mock_session = MagicMock()
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_session.id = 'cs_test_123'
        mock_session.payment_status = 'paid'
        mock_create.return_value = mock_session
        mock_retrieve.return_value = mock_session
        
        self._add_all_to_cart()

        delivery_date = (date.today() + timedelta(days=3)).strftime('%Y-%m-%d')
        self.client.post(reverse('orders:checkout'), {
            'full_name': 'Jane Buyer', 'email': 'c@test.com',
            'address_line1': '5 Market St', 'address_line2': '',
            'city': 'Bristol', 'postcode': 'BS1 1AA',
            'delivery_date': delivery_date,
        })
        
        # Complete payment
        self.client.get(reverse('orders:stripe_success') + '?session_id=cs_test_123')
        order = Order.objects.get(user=self.customer)

        response = self.client.get(reverse('orders:order_detail', args=[order.id]))
        self.assertEqual(response.status_code, 200)

        grouped = response.context['grouped_items']
        self.assertEqual(len(grouped), 2)

        self.assertContains(response, 'Network Commission (5%)')
