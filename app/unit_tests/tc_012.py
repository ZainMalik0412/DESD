from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model

from marketplace.models import Product, Category
from orders.models import Order, OrderItem

CustomUser = get_user_model()


class TC012WeeklySettlementTests(TestCase):
    """
    Test Case ID: TC-012
    User Story: As a producer, I want to receive weekly payment settlements
    so that I can manage my business finances.
    """

    def setUp(self):
        self.client = Client()

        self.producer = CustomUser.objects.create_user(
            username='producer_tc012',
            email='producer_tc012@test.com',
            password='Password123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Jane',
            last_name='Farmer'
        )

        self.other_producer = CustomUser.objects.create_user(
            username='other_producer_tc012',
            email='otherproducer_tc012@test.com',
            password='Password123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Tom',
            last_name='Grower'
        )

        self.customer = CustomUser.objects.create_user(
            username='customer_tc012',
            email='customer_tc012@test.com',
            password='Password123!',
            role=CustomUser.Role.CUSTOMER,
            first_name='Chris',
            last_name='Buyer'
        )

        self.category = Category.objects.create(
            name='Vegetables',
            slug='vegetables',
            description='Fresh vegetables',
            is_active=True
        )

        self.product_1 = Product.objects.create(
            producer=self.producer,
            category=self.category,
            name='Organic Tomatoes',
            description='Fresh tomatoes',
            price=Decimal('4.00'),
            unit=Product.Unit.KG,
            stock_quantity=100,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
        )

        self.product_2 = Product.objects.create(
            producer=self.producer,
            category=self.category,
            name='Organic Carrots',
            description='Fresh carrots',
            price=Decimal('2.00'),
            unit=Product.Unit.KG,
            stock_quantity=100,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
        )

        self.other_producer_product = Product.objects.create(
            producer=self.other_producer,
            category=self.category,
            name='Other Producer Potatoes',
            description='Potatoes',
            price=Decimal('3.00'),
            unit=Product.Unit.KG,
            stock_quantity=100,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
        )

        now = timezone.now()

        # Included in weekly settlement: delivered last week, contains this producer's items
        self.order_1 = Order.objects.create(
            user=self.customer,
            full_name='Chris Buyer',
            email='customer_tc012@test.com',
            address_line1='10 High Street',
            address_line2='',
            city='Bristol',
            postcode='BS1 5JG',
            total=Decimal('20.00'),
            commission=Decimal('1.00'),
            delivery_date=(now + timedelta(days=2)).date(),
            status=Order.STATUS_DELIVERED,
        )
        OrderItem.objects.create(
            order=self.order_1,
            product=self.product_1,
            product_name='Organic Tomatoes',
            unit_price=Decimal('4.00'),
            quantity=5,
            line_total=Decimal('20.00'),
        )
        Order.objects.filter(id=self.order_1.id).update(
            created_at=now - timedelta(days=8)
        )

        self.order_2 = Order.objects.create(
            user=self.customer,
            full_name='Chris Buyer',
            email='customer_tc012@test.com',
            address_line1='10 High Street',
            address_line2='',
            city='Bristol',
            postcode='BS1 5JG',
            total=Decimal('10.00'),
            commission=Decimal('0.50'),
            delivery_date=(now + timedelta(days=3)).date(),
            status=Order.STATUS_DELIVERED,
        )
        OrderItem.objects.create(
            order=self.order_2,
            product=self.product_2,
            product_name='Organic Carrots',
            unit_price=Decimal('2.00'),
            quantity=5,
            line_total=Decimal('10.00'),
        )
        Order.objects.filter(id=self.order_2.id).update(
            created_at=now - timedelta(days=9)
        )

        # Excluded: not delivered
        self.order_3 = Order.objects.create(
            user=self.customer,
            full_name='Chris Buyer',
            email='customer_tc012@test.com',
            address_line1='10 High Street',
            address_line2='',
            city='Bristol',
            postcode='BS1 5JG',
            total=Decimal('99.00'),
            commission=Decimal('4.95'),
            delivery_date=(now + timedelta(days=4)).date(),
            status=Order.STATUS_PENDING,
        )
        OrderItem.objects.create(
            order=self.order_3,
            product=self.product_1,
            product_name='Organic Tomatoes',
            unit_price=Decimal('9.90'),
            quantity=10,
            line_total=Decimal('99.00'),
        )
        Order.objects.filter(id=self.order_3.id).update(
            created_at=now - timedelta(days=8)
        )

        # Excluded: different producer
        self.order_4 = Order.objects.create(
            user=self.customer,
            full_name='Chris Buyer',
            email='customer_tc012@test.com',
            address_line1='10 High Street',
            address_line2='',
            city='Bristol',
            postcode='BS1 5JG',
            total=Decimal('15.00'),
            commission=Decimal('0.75'),
            delivery_date=(now + timedelta(days=2)).date(),
            status=Order.STATUS_DELIVERED,
        )
        OrderItem.objects.create(
            order=self.order_4,
            product=self.other_producer_product,
            product_name='Other Producer Potatoes',
            unit_price=Decimal('3.00'),
            quantity=5,
            line_total=Decimal('15.00'),
        )
        Order.objects.filter(id=self.order_4.id).update(
            created_at=now - timedelta(days=8)
        )

        # Excluded: delivered, but not previous week
        self.order_5 = Order.objects.create(
            user=self.customer,
            full_name='Chris Buyer',
            email='customer_tc012@test.com',
            address_line1='10 High Street',
            address_line2='',
            city='Bristol',
            postcode='BS1 5JG',
            total=Decimal('5.00'),
            commission=Decimal('0.25'),
            delivery_date=(now + timedelta(days=1)).date(),
            status=Order.STATUS_DELIVERED,
        )
        OrderItem.objects.create(
            order=self.order_5,
            product=self.product_1,
            product_name='Organic Tomatoes',
            unit_price=Decimal('5.00'),
            quantity=1,
            line_total=Decimal('5.00'),
        )
        Order.objects.filter(id=self.order_5.id).update(
            created_at=now - timedelta(days=2)
        )

        self.payments_url = "/orders/payments/"
        self.csv_report_url = "/orders/payments/report/csv/"

    def test_producer_can_access_weekly_payments_page(self):
        """
        Producer logs in and opens Payments / Financial Reports section.
        Expected to fail right now if the page does not exist yet.
        """
        self.client.login(username='producer_tc012', password='Password123!')
        response = self.client.get(self.payments_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payments')
        self.assertContains(response, 'Financial Reports')

    def test_weekly_settlement_only_includes_delivered_orders_from_previous_week(self):
        """
        Only delivered/completed orders from the previous week for this producer
        should appear in the weekly settlement summary.
        """
        self.client.login(username='producer_tc012', password='Password123!')
        response = self.client.get(self.payments_url)

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, f"Order {self.order_1.id} -")
        self.assertContains(response, f"Order {self.order_2.id} -")

        self.assertNotContains(response, f"Order {self.order_3.id} -")  
        self.assertNotContains(response, f"Order {self.order_4.id} -")  
        self.assertNotContains(response, f"Order {self.order_5.id} -")  

    def test_weekly_summary_shows_correct_commission_and_producer_payment(self):
        """
        Weekly summary should show:
        total orders value = 30.00
        commission = 1.50
        producer payment = 28.50
        """
        self.client.login(username='producer_tc012', password='Password123!')
        response = self.client.get(self.payments_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '30.00')
        self.assertContains(response, '1.50')
        self.assertContains(response, '28.50')

    def test_payment_status_and_tax_year_total_are_displayed(self):
        """
        Weekly settlement page should show payment status and running yearly total.
        """
        self.client.login(username='producer_tc012', password='Password123!')
        response = self.client.get(self.payments_url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            'Processed' in response.content.decode() or 'Pending Bank Transfer' in response.content.decode()
        )
        self.assertContains(response, 'Tax Year Total')

    def test_csv_payment_report_can_be_downloaded(self):
        """
        Producer should be able to download a payment report for tax records.
        """
        self.client.login(username='producer_tc012', password='Password123!')
        response = self.client.get(self.csv_report_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertContains(response, 'order')
        self.assertContains(response, 'commission')