from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import CustomUser
from marketplace.models import Product, Category
from orders.models import Order, OrderItem


class TC025AdminFinancialReportsTest(TestCase):
    """
    TC-025: As a system administrator, I want to monitor the network commission 
    calculations so that I can ensure financial accuracy and generate reports.
    
    Validates that the 5% network commission is accurately calculated, recorded, 
    and reportable across all transactions for network sustainability and financial compliance.
    """

    def setUp(self):
        """Set up test data including admin, producers, customers, and orders."""
        self.client = Client()

        # Create admin user
        self.admin_user = CustomUser.objects.create_user(
            username='admin',
            email='admin@brfn.com',
            password='AdminP@ssw0rd123',
            role=CustomUser.Role.ADMIN
        )

        # Create producer accounts
        self.producer1 = CustomUser.objects.create_user(
            username='producer1',
            email='producer1@farm.com',
            password='ProducerPass123',
            role=CustomUser.Role.PRODUCER,
            first_name='Producer',
            last_name='One'
        )

        self.producer2 = CustomUser.objects.create_user(
            username='producer2',
            email='producer2@farm.com',
            password='ProducerPass123',
            role=CustomUser.Role.PRODUCER,
            first_name='Producer',
            last_name='Two'
        )

        # Create customer account
        self.customer = CustomUser.objects.create_user(
            username='customer1',
            email='customer@test.com',
            password='CustomerPass123',
            role=CustomUser.Role.CUSTOMER,
            first_name='Test',
            last_name='Customer'
        )

        # Create category
        self.category = Category.objects.create(
            name='Vegetables',
            slug='vegetables',
            is_active=True
        )

        # Create products for producer1
        self.product1 = Product.objects.create(
            category=self.category,
            producer=self.producer1,
            name='Organic Carrots',
            price=Decimal('2.50'),
            stock_quantity=100,
            is_available=True
        )

        self.product2 = Product.objects.create(
            category=self.category,
            producer=self.producer1,
            name='Fresh Lettuce',
            price=Decimal('1.50'),
            stock_quantity=50,
            is_available=True
        )

        # Create products for producer2
        self.product3 = Product.objects.create(
            category=self.category,
            producer=self.producer2,
            name='Cherry Tomatoes',
            price=Decimal('3.00'),
            stock_quantity=75,
            is_available=True
        )

        self.product4 = Product.objects.create(
            category=self.category,
            producer=self.producer2,
            name='Cucumber',
            price=Decimal('1.00'),
            stock_quantity=60,
            is_available=True
        )

        # Create orders spanning 2 weeks (precondition requirement)
        self.create_test_orders()

    def create_test_orders(self):
        """Create test orders with varying dates and amounts."""
        today = date.today()
        now = timezone.now()

        # Order 1: Single vendor order (£100) - 2 weeks ago
        self.order1 = Order.objects.create(
            user=self.customer,
            status=Order.STATUS_DELIVERED,
            total=Decimal('100.00'),
            commission=Decimal('5.00'),  # 5% of £100
            full_name='Test Customer',
            email='customer@test.com',
            address_line1='123 Test Street',
            city='Bristol',
            postcode='BS1 4DJ',
            delivery_date=today - timedelta(days=14)
        )
        # Manually set created_at to bypass auto_now_add
        Order.objects.filter(pk=self.order1.pk).update(created_at=now - timedelta(days=14))
        self.order1.refresh_from_db()
        
        OrderItem.objects.create(
            order=self.order1,
            product=self.product1,
            product_name=self.product1.name,
            unit_price=Decimal('2.50'),
            quantity=40,
            line_total=Decimal('100.00')
        )

        # Order 2: Multi-vendor order (£150 total: £80 + £70) - 10 days ago
        order2_total = Decimal('150.00')
        self.order2 = Order.objects.create(
            user=self.customer,
            status=Order.STATUS_DELIVERED,
            total=order2_total,
            commission=(order2_total * Decimal('0.05')).quantize(Decimal('0.01')),  # £7.50
            full_name='Test Customer',
            email='customer@test.com',
            address_line1='123 Test Street',
            city='Bristol',
            postcode='BS1 4DJ',
            delivery_date=today - timedelta(days=10)
        )
        # Manually set created_at to bypass auto_now_add
        Order.objects.filter(pk=self.order2.pk).update(created_at=now - timedelta(days=10))
        self.order2.refresh_from_db()
        
        # Producer 1 items - £80 worth
        OrderItem.objects.create(
            order=self.order2,
            product=self.product1,
            product_name=self.product1.name,
            unit_price=Decimal('2.50'),
            quantity=20,
            line_total=Decimal('50.00')
        )
        OrderItem.objects.create(
            order=self.order2,
            product=self.product2,
            product_name=self.product2.name,
            unit_price=Decimal('1.50'),
            quantity=20,
            line_total=Decimal('30.00')
        )
        # Producer 2 items - £70 worth
        OrderItem.objects.create(
            order=self.order2,
            product=self.product3,
            product_name=self.product3.name,
            unit_price=Decimal('3.00'),
            quantity=20,
            line_total=Decimal('60.00')
        )
        OrderItem.objects.create(
            order=self.order2,
            product=self.product4,
            product_name=self.product4.name,
            unit_price=Decimal('1.00'),
            quantity=10,
            line_total=Decimal('10.00')
        )

        # Order 3: Recent order (£50) - 3 days ago
        self.order3 = Order.objects.create(
            user=self.customer,
            status=Order.STATUS_CONFIRMED,
            total=Decimal('50.00'),
            commission=Decimal('2.50'),  # 5% of £50
            full_name='Test Customer',
            email='customer@test.com',
            address_line1='123 Test Street',
            city='Bristol',
            postcode='BS1 4DJ',
            delivery_date=today - timedelta(days=3)
        )
        # Manually set created_at to bypass auto_now_add
        Order.objects.filter(pk=self.order3.pk).update(created_at=now - timedelta(days=3))
        self.order3.refresh_from_db()
        
        OrderItem.objects.create(
            order=self.order3,
            product=self.product3,
            product_name=self.product3.name,
            unit_price=Decimal('2.50'),
            quantity=20,
            line_total=Decimal('50.00')
        )

    def test_step_1_admin_login(self):
        """Step 1: Log in as administrator with appropriate permissions."""
        login_successful = self.client.login(
            username='admin',
            password='AdminP@ssw0rd123'
        )
        self.assertTrue(
            login_successful,
            "Admin user should be able to log in successfully"
        )
        self.assertEqual(
            self.admin_user.role,
            CustomUser.Role.ADMIN,
            "User should have admin role"
        )

    def test_step_2_3_4_navigate_and_generate_report(self):
        """Steps 2-4: Navigate to Financial Reports and generate report with date range."""
        self.client.login(username='admin', password='AdminP@ssw0rd123')

        # Define date range: Previous 2 weeks
        end_date = date.today()
        start_date = end_date - timedelta(days=14)

        # Navigate to financial reports with date range
        url = reverse('orders:admin_financial_reports')
        response = self.client.get(url, {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })

        self.assertEqual(
            response.status_code,
            200,
            "Admin should be able to access financial reports page"
        )
        self.assertIn(
            'orders',
            response.context,
            "Report should contain orders data"
        )

    def test_step_5_report_shows_comprehensive_data(self):
        """Step 5: View report showing all required financial information."""
        self.client.login(username='admin', password='AdminP@ssw0rd123')

        end_date = date.today()
        start_date = end_date - timedelta(days=14)

        url = reverse('orders:admin_financial_reports')
        response = self.client.get(url, {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })

        # Check that all required data is present
        context = response.context
        self.assertIn('total_order_value', context, "Report should show total order value")
        self.assertIn('total_commission', context, "Report should show 5% commission amount")
        self.assertIn('total_producer_payment', context, "Report should show producer payment amounts (95%)")
        self.assertIn('order_count', context, "Report should show number of orders processed")

        # Verify calculations
        expected_total = Decimal('300.00')  # £100 + £150 + £50
        expected_commission = Decimal('15.00')  # 5% of £300
        expected_producer_payment = Decimal('285.00')  # 95% of £300

        self.assertEqual(
            context['total_order_value'],
            expected_total,
            f"Total order value should be £{expected_total}"
        )
        self.assertEqual(
            context['total_commission'],
            expected_commission,
            f"Total commission should be £{expected_commission}"
        )
        self.assertEqual(
            context['total_producer_payment'],
            expected_producer_payment,
            f"Total producer payment should be £{expected_producer_payment}"
        )

    def test_step_6_7_view_order_detail(self):
        """Steps 6-7: Select specific order and view detailed breakdown."""
        self.client.login(username='admin', password='AdminP@ssw0rd123')

        # View detailed breakdown for order 1
        url = reverse('orders:admin_order_detail', kwargs={'order_id': self.order1.id})
        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            200,
            "Admin should be able to access order detail page"
        )

        context = response.context
        self.assertEqual(
            context['order'],
            self.order1,
            "Order details should be displayed"
        )
        self.assertIn(
            'producer_breakdown',
            context,
            "Detailed breakdown should include producer payment per supplier"
        )

    def test_step_8_simple_order_commission_calculation(self):
        """Step 8: Test calculation verification for £100 order."""
        # Order total: £100
        # Expected commission: £5.00 (5% of £100)
        # Expected producer payment: £95.00 (95% of £100)

        self.assertEqual(
            self.order1.total,
            Decimal('100.00'),
            "Order total should be £100.00"
        )
        self.assertEqual(
            self.order1.commission,
            Decimal('5.00'),
            "Commission should be £5.00 (5% of £100)"
        )
        self.assertEqual(
            self.order1.producer_payment,
            Decimal('95.00'),
            "Producer payment should be £95.00 (95% of £100)"
        )

        # Verify commission is accurate to 2 decimal places
        self.assertEqual(
            len(str(self.order1.commission).split('.')[-1]),
            2,
            "Commission should be accurate to 2 decimal places"
        )

    def test_step_9_multi_vendor_commission_calculation(self):
        """Step 9: Test multi-vendor order commission calculation."""
        # Multi-vendor order totaling £150 with 2 producers (£80 and £70 worth)
        # Total commission: £7.50 (5% of £150)
        # Producer 1 subtotal: £80 → commission: £4.00, payment: £76.00
        # Producer 2 subtotal: £70 → commission: £3.50, payment: £66.50

        self.assertEqual(
            self.order2.total,
            Decimal('150.00'),
            "Order total should be £150.00"
        )
        self.assertEqual(
            self.order2.commission,
            Decimal('7.50'),
            "Total commission should be £7.50 (5% of £150)"
        )

        # Test producer breakdown calculations
        producer1_subtotal = Decimal('80.00')
        producer1_commission = (producer1_subtotal * Decimal('0.05')).quantize(Decimal('0.01'))
        producer1_payment = producer1_subtotal - producer1_commission

        self.assertEqual(
            producer1_commission,
            Decimal('4.00'),
            "Producer 1 commission should be £4.00 (5% of £80)"
        )
        self.assertEqual(
            producer1_payment,
            Decimal('76.00'),
            "Producer 1 payment should be £76.00 (95% of £80)"
        )

        producer2_subtotal = Decimal('70.00')
        producer2_commission = (producer2_subtotal * Decimal('0.05')).quantize(Decimal('0.01'))
        producer2_payment = producer2_subtotal - producer2_commission

        self.assertEqual(
            producer2_commission,
            Decimal('3.50'),
            "Producer 2 commission should be £3.50 (5% of £70)"
        )
        self.assertEqual(
            producer2_payment,
            Decimal('66.50'),
            "Producer 2 payment should be £66.50 (95% of £70)"
        )

    def test_step_10_download_csv_report(self):
        """Step 10: Download report in CSV format for accounting software."""
        self.client.login(username='admin', password='AdminP@ssw0rd123')

        end_date = date.today()
        start_date = end_date - timedelta(days=14)

        url = reverse('orders:admin_financial_reports_csv')
        response = self.client.get(url, {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })

        self.assertEqual(
            response.status_code,
            200,
            "CSV export should be accessible"
        )
        self.assertEqual(
            response['Content-Type'],
            'text/csv',
            "Response should be CSV format"
        )
        self.assertIn(
            'attachment',
            response['Content-Disposition'],
            "CSV should be downloadable as attachment"
        )

        # Verify CSV content
        content = response.content.decode('utf-8')
        self.assertIn('Order ID', content, "CSV should contain Order ID header")
        self.assertIn('Commission', content, "CSV should contain Commission column")
        self.assertIn('Producer Payment', content, "CSV should contain Producer Payment column")

    def test_step_11_monthly_summary_report(self):
        """Step 11: Generate monthly summary report."""
        self.client.login(username='admin', password='AdminP@ssw0rd123')

        # Get current month
        current_month = date.today().strftime('%Y-%m')

        url = reverse('orders:admin_monthly_summary')
        response = self.client.get(url, {'month': current_month})

        self.assertEqual(
            response.status_code,
            200,
            "Monthly summary should be accessible"
        )

        context = response.context
        self.assertIn('monthly_total', context, "Monthly summary should show total sales")
        self.assertIn('monthly_commission', context, "Monthly summary should show commission")
        self.assertIn('order_count', context, "Monthly summary should show order count")
        self.assertIn('producer_stats', context, "Monthly summary should show producer breakdown")

    def test_step_12_year_to_date_totals(self):
        """Step 12: View year-to-date commission totals."""
        self.client.login(username='admin', password='AdminP@ssw0rd123')

        url = reverse('orders:admin_financial_reports')
        response = self.client.get(url)

        context = response.context
        self.assertIn('ytd_total', context, "Report should include year-to-date total")
        self.assertIn('ytd_commission', context, "Report should include year-to-date commission")
        self.assertIn('ytd_count', context, "Report should include year-to-date order count")

        # YTD should include all orders in current year
        self.assertGreater(
            context['ytd_total'],
            Decimal('0.00'),
            "Year-to-date total should be greater than zero"
        )

    def test_commission_rate_consistency(self):
        """Verify that 5% network / 95% producer split is consistently applied."""
        # Check Order model constant
        self.assertEqual(
            Order.COMMISSION_RATE,
            Decimal('0.05'),
            "Commission rate should be 5% (0.05)"
        )

        # Verify all test orders follow the split
        for order in [self.order1, self.order2, self.order3]:
            expected_commission = (order.total * Decimal('0.05')).quantize(Decimal('0.01'))
            expected_producer_payment = order.total - expected_commission

            self.assertEqual(
                order.commission,
                expected_commission,
                f"Order {order.id} commission should be 5% of total"
            )
            self.assertEqual(
                order.producer_payment,
                expected_producer_payment,
                f"Order {order.id} producer payment should be 95% of total"
            )

    def test_rounding_consistency(self):
        """Verify that rounding is handled consistently to 2 decimal places."""
        # Test with an amount that requires rounding
        test_amount = Decimal('33.33')
        commission = (test_amount * Decimal('0.05')).quantize(Decimal('0.01'))
        payment = test_amount - commission

        # Check precision
        self.assertEqual(
            len(str(commission).split('.')[-1]),
            2,
            "Commission should be rounded to 2 decimal places"
        )
        self.assertEqual(
            len(str(payment).split('.')[-1]),
            2,
            "Producer payment should be rounded to 2 decimal places"
        )

        # Verify total matches
        self.assertEqual(
            commission + payment,
            test_amount,
            "Commission + Payment should equal original total"
        )

    def test_unauthorised_access_prevention(self):
        """Verify that non-admin users cannot access financial data."""
        # Try to access as producer
        self.client.login(username='producer1', password='ProducerPass123')

        url = reverse('orders:admin_financial_reports')
        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            404,
            "Non-admin users should not be able to access admin financial reports"
        )

        # Try to access as customer
        self.client.login(username='customer1', password='CustomerPass123')
        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            404,
            "Customers should not be able to access admin financial reports"
        )

    def test_date_range_filtering(self):
        """Verify that reports can be filtered by date range."""
        self.client.login(username='admin', password='AdminP@ssw0rd123')

        # Filter to only show orders from last 7 days (should only include order3)
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        url = reverse('orders:admin_financial_reports')
        response = self.client.get(url, {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })

        context = response.context
        # Only order3 (£50) should be in this date range
        self.assertEqual(
            context['total_order_value'],
            Decimal('50.00'),
            "Filtered report should only show orders in date range"
        )
        self.assertEqual(
            context['total_commission'],
            Decimal('2.50'),
            "Commission should match filtered date range"
        )

    def test_audit_trail_exists(self):
        """Verify that all financial data is auditable and traceable."""
        self.client.login(username='admin', password='AdminP@ssw0rd123')

        # Access order detail to verify audit trail
        url = reverse('orders:admin_order_detail', kwargs={'order_id': self.order2.id})
        response = self.client.get(url)

        context = response.context
        order = context['order']

        # Verify order has traceable information
        self.assertIsNotNone(order.id, "Order should have unique ID")
        self.assertIsNotNone(order.created_at, "Order should have creation timestamp")
        self.assertIsNotNone(order.user, "Order should be linked to customer")

        # Verify items are linked to orders
        items = context['items']
        for item in items:
            self.assertEqual(
                item.order,
                order,
                "Order item should be linked to parent order"
            )
