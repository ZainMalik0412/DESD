from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from marketplace.models import Product, Category
from orders.models import Order, OrderItem, StatusUpdate


CustomUser = get_user_model()


class TC010OrderStatusUpdateTests(TestCase):
    """
    Test Case ID: TC-010
    """

    def setUp(self):
        self.client = Client()

        self.producer = CustomUser.objects.create_user(
            username='producer_tc10', email='p@test.com', password='Password123!',
            role=CustomUser.Role.PRODUCER, first_name='Jane', last_name='Farm'
        )
        self.producer2 = CustomUser.objects.create_user(
            username='producer2_tc10', email='p2@test.com', password='Password123!',
            role=CustomUser.Role.PRODUCER
        )
        self.customer = CustomUser.objects.create_user(
            username='customer_tc10', email='c@test.com', password='Password123!',
            role=CustomUser.Role.CUSTOMER, first_name='Bob', last_name='Smith'
        )

        self.category = Category.objects.create(name='Veg', slug='veg')
        self.product = Product.objects.create(
            producer=self.producer, category=self.category,
            name='Tomatoes', price=Decimal('2.50'), stock_quantity=100
        )
        self.product2 = Product.objects.create(
            producer=self.producer2, category=self.category,
            name='Lettuce', price=Decimal('1.00'), stock_quantity=100
        )

        self.order = Order.objects.create(
            user=self.customer, full_name='Bob Smith', email='c@test.com',
            address_line1='5 Garden Rd', city='Bristol', postcode='BS4 4DD',
            total=Decimal('5.00'), delivery_date=date.today() + timedelta(days=5),
            status=Order.STATUS_PENDING
        )
        OrderItem.objects.create(
            order=self.order, product=self.product, product_name='Tomatoes',
            unit_price=Decimal('2.50'), quantity=2, line_total=Decimal('5.00')
        )

    def test_full_status_lifecycle_with_audit_trail(self):
        """Tests Pending->Confirmed->Ready->Delivered with StatusUpdate records created at each step."""
        self.client.login(username='producer_tc10', password='Password123!')

        transitions = [
            (Order.STATUS_CONFIRMED, 'Products will be prepared by delivery date'),
            (Order.STATUS_READY, 'Ready for collection'),
            (Order.STATUS_DELIVERED, ''),
        ]

        for new_status, note in transitions:
            old_status = Order.objects.get(id=self.order.id).status
            self.client.post(reverse('orders:manage_order_detail', args=[self.order.id]), {
                'status': new_status,
                'note': note,
            })
            self.order.refresh_from_db()
            self.assertEqual(self.order.status, new_status)

            update = StatusUpdate.objects.filter(order=self.order, new_status=new_status).first()
            self.assertIsNotNone(update)
            self.assertEqual(update.old_status, old_status)
            self.assertEqual(update.changed_by, self.producer)
            self.assertEqual(update.note, note)
            self.assertIsNotNone(update.created_at)

    def test_notes_are_saved(self):
        """Verifies optional notes are persisted on the StatusUpdate."""
        self.client.login(username='producer_tc10', password='Password123!')

        self.client.post(reverse('orders:manage_order_detail', args=[self.order.id]), {
            'status': Order.STATUS_CONFIRMED,
            'note': 'Special handling required',
        })

        update = StatusUpdate.objects.get(order=self.order)
        self.assertEqual(update.note, 'Special handling required')

    def test_status_cannot_skip_stages(self):
        """Verifies status cannot jump from Pending directly to Delivered."""
        self.client.login(username='producer_tc10', password='Password123!')

        self.client.post(reverse('orders:manage_order_detail', args=[self.order.id]), {
            'status': Order.STATUS_DELIVERED,
        })
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PENDING)
        self.assertEqual(StatusUpdate.objects.filter(order=self.order).count(), 0)

    def test_customer_sees_updated_status_and_history(self):
        """Customer order detail reflects the latest status and shows the status history timeline."""
        # Producer updates status
        self.client.login(username='producer_tc10', password='Password123!')
        self.client.post(reverse('orders:manage_order_detail', args=[self.order.id]), {
            'status': Order.STATUS_CONFIRMED,
            'note': 'Being prepared now',
        })
        self.client.logout()

        # Customer views their order
        self.client.login(username='customer_tc10', password='Password123!')
        response = self.client.get(reverse('orders:order_detail', args=[self.order.id]))
        self.assertEqual(response.status_code, 200)

        # Status is reflected
        self.assertContains(response, 'Confirmed')
        # History is visible
        self.assertContains(response, 'Being prepared now')
        # Status updates are in context
        self.assertEqual(len(response.context['status_updates']), 1)

    def test_only_relevant_producer_can_update(self):
        """Producer2 cannot update an order that only contains Producer1's products."""
        self.client.login(username='producer2_tc10', password='Password123!')

        response = self.client.post(reverse('orders:manage_order_detail', args=[self.order.id]), {
            'status': Order.STATUS_CONFIRMED,
        })
        self.assertEqual(response.status_code, 404)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PENDING)

    def test_producer_dashboard_shows_status(self):
        """The manage_orders list view reflects the current status display."""
        self.client.login(username='producer_tc10', password='Password123!')

        # Update to confirmed first
        self.client.post(reverse('orders:manage_order_detail', args=[self.order.id]), {
            'status': Order.STATUS_CONFIRMED,
        })

        response = self.client.get(reverse('orders:manage_orders'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirmed')

    def test_status_history_logged_with_timestamp_and_producer(self):
        """Each StatusUpdate entry has a timestamp and the producer who made the change."""
        self.client.login(username='producer_tc10', password='Password123!')

        self.client.post(reverse('orders:manage_order_detail', args=[self.order.id]), {
            'status': Order.STATUS_CONFIRMED,
        })

        update = StatusUpdate.objects.get(order=self.order)
        self.assertIsNotNone(update.created_at)
        self.assertEqual(update.changed_by, self.producer)
        self.assertEqual(update.changed_by.username, 'producer_tc10')
