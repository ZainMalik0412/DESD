from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from marketplace.models import Product, Category
from orders.models import Cart, CartItem, Order, OrderItem


CustomUser = get_user_model()


class TC009ProducerDashboardTests(TestCase):
    """
    Test Case ID: TC-009
    User Story: As a producer, I want to view incoming orders so that I can prepare products for delivery.
    Description: Validates that producers can access a dashboard showing all incoming orders with adequate lead time, and complete details.
    """

    def setUp(self):
        self.client = Client()

        self.producer1 = CustomUser.objects.create_user(
            username='producer1', email='p1@test.com', password='Password123!', role=CustomUser.Role.PRODUCER,
            first_name='Peter', last_name='Piper', delivery_address='1 Farm Ln', postcode='BS1 1AA'
        )
        self.producer2 = CustomUser.objects.create_user(
            username='producer2', email='p2@test.com', password='Password123!', role=CustomUser.Role.PRODUCER
        )
        self.customer = CustomUser.objects.create_user(
            username='test_customer', email='customer@test.com', password='Password123!', role=CustomUser.Role.CUSTOMER,
            first_name='John', last_name='Doe', delivery_address='10 High St', postcode='BS2 2BB'
        )

        self.category = Category.objects.create(name='Produce', slug='produce')
        
        self.p1_product_1 = Product.objects.create(producer=self.producer1, category=self.category, name='Apples', price=Decimal('2.00'), stock_quantity=50)
        self.p1_product_2 = Product.objects.create(producer=self.producer1, category=self.category, name='Pears', price=Decimal('3.00'), stock_quantity=50)
        
        self.p2_product_1 = Product.objects.create(producer=self.producer2, category=self.category, name='Bananas', price=Decimal('1.50'), stock_quantity=50)

        self.today = date.today()
        d1 = self.today + timedelta(days=5)
        d2 = self.today + timedelta(days=3)
        d3 = self.today + timedelta(days=7)
        
        self.order1 = Order.objects.create(
            user=self.customer, full_name='John Doe', email='j@test.com', address_line1='10 High St', city='Bristol', postcode='BS2 2BB',
            total=Decimal('4.00'), delivery_date=d1, status=Order.STATUS_PENDING
        )
        OrderItem.objects.create(order=self.order1, product=self.p1_product_1, product_name='Apples', unit_price=Decimal('2.00'), quantity=2, line_total=Decimal('4.00'))

        self.order2 = Order.objects.create(
            user=self.customer, full_name='John Doe', email='j@test.com', address_line1='10 High St', city='Bristol', postcode='BS2 2BB',
            total=Decimal('6.00'), delivery_date=d2, status=Order.STATUS_CONFIRMED
        )
        OrderItem.objects.create(order=self.order2, product=self.p1_product_2, product_name='Pears', unit_price=Decimal('3.00'), quantity=1, line_total=Decimal('3.00'))
        OrderItem.objects.create(order=self.order2, product=self.p2_product_1, product_name='Bananas', unit_price=Decimal('1.50'), quantity=2, line_total=Decimal('3.00'))

        self.order3 = Order.objects.create(
            user=self.customer, full_name='John Doe', email='j@test.com', address_line1='10 High St', city='Bristol', postcode='BS2 2BB',
            total=Decimal('10.00'), delivery_date=d3, status=Order.STATUS_READY
        )
        OrderItem.objects.create(order=self.order3, product=self.p1_product_1, product_name='Apples', unit_price=Decimal('2.00'), quantity=5, line_total=Decimal('10.00'))

        self.order4 = Order.objects.create(
            user=self.customer, full_name='Other Person', email='o@test.com', address_line1='10 Other St', city='Bristol', postcode='BS3 3CC',
            total=Decimal('1.50'), delivery_date=d1, status=Order.STATUS_PENDING
        )
        OrderItem.objects.create(order=self.order4, product=self.p2_product_1, product_name='Bananas', unit_price=Decimal('1.50'), quantity=1, line_total=Decimal('1.50'))


    @patch('stripe.checkout.Session.create')
    @patch('stripe.checkout.Session.retrieve')
    def test_tc009_lead_time_checkout_validation(self, mock_retrieve, mock_create):
        """Verifies explicitly that 48-hour lead time from order date is strictly enforced."""
        # Mock Stripe responses
        mock_session = MagicMock()
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_session.id = 'cs_test_123'
        mock_session.payment_status = 'paid'
        mock_create.return_value = mock_session
        mock_retrieve.return_value = mock_session
        
        self.client.login(username='test_customer', password='Password123!')
        
        cart, _ = Cart.objects.get_or_create(user=self.customer, status=Cart.STATUS_ACTIVE)
        CartItem.objects.create(cart=cart, product=self.p1_product_1, quantity=1)
        
        bad_date = (self.today + timedelta(days=1)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('orders:checkout'), {
            'full_name': 'Test', 'email': 'test@test.com', 'address_line1': '10 St', 'city': 'Bristol', 'postcode': 'BS1 1AA',
            'delivery_date': bad_date
        })
        self.assertEqual(Cart.objects.filter(user=self.customer, status=Cart.STATUS_ACTIVE).exists(), True)

        good_date = (self.today + timedelta(days=2)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('orders:checkout'), {
            'full_name': 'Test', 'email': 'test@test.com', 'address_line1': '10 St', 'city': 'Bristol', 'postcode': 'BS1 1AA',
            'delivery_date': good_date
        })
        
        # Complete payment
        self.client.get(reverse('orders:stripe_success') + '?session_id=cs_test_123')
        self.assertEqual(Cart.objects.filter(user=self.customer, status=Cart.STATUS_ACTIVE).exists(), False)


    def test_tc009_producer_dashboard_visibility(self):
        """Verifies producer login and list of incoming orders mapping to rules"""
        self.client.login(username='producer1', password='Password123!')
        
        response = self.client.get(reverse('orders:manage_orders'))
        self.assertEqual(response.status_code, 200)
        
        orders_context = list(response.context['orders'])
        
        self.assertEqual(len(orders_context), 3)
        self.assertNotIn(self.order4, orders_context)
        
        self.assertEqual(orders_context[0], self.order2)
        self.assertEqual(orders_context[1], self.order1)
        self.assertEqual(orders_context[2], self.order3)

    def test_tc009_producer_order_detail_multivendor(self):
        """Verifies that within a multi-vendor order, the producer only views their items."""
        self.client.login(username='producer1', password='Password123!')
        
        response = self.client.get(reverse('orders:manage_order_detail', args=[self.order2.id]))
        self.assertEqual(response.status_code, 200)

        items_context = list(response.context['items'])
        self.assertEqual(len(items_context), 1)
        self.assertEqual(items_context[0].product_name, 'Pears')

        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'j@test.com')
        self.assertContains(response, '10 High St')

    def test_tc009_order_status_progression(self):
        """Producer can update statuses correctly following the allowed state transitions through to Delivered"""
        self.client.login(username='producer1', password='Password123!')
        
        response = self.client.post(reverse('orders:manage_order_detail', args=[self.order1.id]), {
            'status': Order.STATUS_CONFIRMED
        })
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, Order.STATUS_CONFIRMED)

        response = self.client.post(reverse('orders:manage_order_detail', args=[self.order1.id]), {
            'status': Order.STATUS_READY
        })
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, Order.STATUS_READY)

        response = self.client.post(reverse('orders:manage_order_detail', args=[self.order1.id]), {
            'status': Order.STATUS_DELIVERED
        })
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, Order.STATUS_DELIVERED)

