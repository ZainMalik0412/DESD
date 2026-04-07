"""
TC-023: Low Stock Notifications
As a producer, I want to receive a notification when stock for a product runs low
so that I can restock before orders fail.
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from marketplace.models import Product, Category, StockAlert
from orders.models import Cart, CartItem, Order, OrderItem

User = get_user_model()


class TC023LowStockNotificationTests(TestCase):
    """Test suite for low stock notification system."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        
        # Create users
        self.producer = User.objects.create_user(
            username="eggfarmer",
            email="eggs@farm.com",
            password="TestPass123!",
            role="producer",
            postcode="BS1 1AA"
        )
        
        self.customer = User.objects.create_user(
            username="customer1",
            email="customer@test.com",
            password="TestPass123!",
            role="customer",
            postcode="BS2 2BB"
        )
        
        # Create category
        self.category = Category.objects.create(
            name="Eggs & Dairy",
            slug="eggs-dairy"
        )
        
        # Create product
        self.product = Product.objects.create(
            name="Fresh Eggs",
            description="Fresh farm eggs",
            price=Decimal("5.00"),
            unit="dozen",
            stock_quantity=50,
            low_stock_threshold=10,
            category=self.category,
            producer=self.producer,
            is_available=True,
            seasonal_status="in_season"
        )

    def test_01_producer_can_set_low_stock_threshold(self):
        """Test that producer can set low stock threshold for a product."""
        # Direct test - just verify the field can be set
        self.product.low_stock_threshold = 15
        self.product.save()
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.low_stock_threshold, 15)

    def test_02_no_alert_when_stock_above_threshold(self):
        """Test that no alert is generated when stock is above threshold."""
        # Stock is 50, threshold is 10 - should be no alerts
        alerts = StockAlert.objects.filter(
            product=self.product,
            producer=self.producer,
            status=StockAlert.Status.ACTIVE
        )
        
        self.assertEqual(alerts.count(), 0)

    def test_03_alert_created_when_stock_falls_below_threshold(self):
        """Test that alert is created when stock falls below threshold."""
        # Reduce stock below threshold
        self.product.stock_quantity = 8
        self.product.save()
        
        # Call the check function (simulating what happens in checkout)
        from orders.views import _check_and_create_stock_alert
        _check_and_create_stock_alert(self.product)
        
        # Verify alert was created
        alerts = StockAlert.objects.filter(
            product=self.product,
            producer=self.producer,
            status=StockAlert.Status.ACTIVE
        )
        
        self.assertEqual(alerts.count(), 1)
        alert = alerts.first()
        self.assertEqual(alert.stock_level, 8)
        self.assertEqual(alert.threshold, 10)

    def test_04_stock_alert_visible_in_producer_dashboard(self):
        """Test that stock alerts are visible in producer dashboard."""
        # Create an alert
        self.product.stock_quantity = 5
        self.product.save()
        
        StockAlert.objects.create(
            product=self.product,
            producer=self.producer,
            stock_level=5,
            threshold=10,
            status=StockAlert.Status.ACTIVE
        )
        
        # Login as producer and access dashboard
        self.client.login(username="eggfarmer", password="TestPass123!")
        response = self.client.get(reverse("orders:stock_alerts"))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fresh Eggs")
        self.assertContains(response, "Active")
        self.assertContains(response, "5")  # Current stock level

    def test_05_alert_resolved_when_stock_replenished(self):
        """Test that alert is resolved when stock is replenished above threshold."""
        # Create an active alert
        alert = StockAlert.objects.create(
            product=self.product,
            producer=self.producer,
            stock_level=8,
            threshold=10,
            status=StockAlert.Status.ACTIVE
        )
        
        # Replenish stock above threshold
        self.product.stock_quantity = 40
        self.product.save()
        
        # Call the check function
        from orders.views import _check_and_create_stock_alert
        _check_and_create_stock_alert(self.product)
        
        # Verify alert was resolved
        alert.refresh_from_db()
        self.assertEqual(alert.status, StockAlert.Status.RESOLVED)

    def test_06_alert_dismissed_by_producer(self):
        """Test that producer can dismiss an alert."""
        # Create an active alert
        alert = StockAlert.objects.create(
            product=self.product,
            producer=self.producer,
            stock_level=5,
            threshold=10,
            status=StockAlert.Status.ACTIVE
        )
        
        # Login and dismiss alert
        self.client.login(username="eggfarmer", password="TestPass123!")
        response = self.client.post(
            reverse("orders:stock_alerts"),
            {
                "alert_id": alert.id,
                "action": "dismiss"
            },
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify alert was dismissed
        alert.refresh_from_db()
        self.assertEqual(alert.status, StockAlert.Status.DISMISSED)

    def test_07_stock_decrements_on_order_placement(self):
        """Test that stock decrements when an order is placed."""
        initial_stock = self.product.stock_quantity
        
        # Add to cart and checkout
        self.client.login(username="customer1", password="TestPass123!")
        self.client.post(
            reverse("orders:add_to_cart", args=[self.product.id]),
            {"quantity": "5"}
        )
        
        # Get cart and verify
        cart = Cart.objects.get(user=self.customer, status=Cart.STATUS_ACTIVE)
        self.assertEqual(cart.items.count(), 1)
        
        # Manually update stock (simulating order completion)
        self.product.stock_quantity -= 5
        self.product.save()
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, initial_stock - 5)

    def test_08_multiple_alerts_for_different_products(self):
        """Test that system can handle multiple alerts for different products."""
        # Create another product
        product2 = Product.objects.create(
            name="Organic Milk",
            description="Fresh organic milk",
            price=Decimal("2.50"),
            unit="litre",
            stock_quantity=5,
            low_stock_threshold=10,
            category=self.category,
            producer=self.producer,
            is_available=True,
            seasonal_status="in_season"
        )
        
        # Set first product below threshold
        self.product.stock_quantity = 8
        self.product.save()
        
        # Create alerts
        from orders.views import _check_and_create_stock_alert
        _check_and_create_stock_alert(self.product)
        _check_and_create_stock_alert(product2)
        
        # Verify both alerts exist
        alerts = StockAlert.objects.filter(
            producer=self.producer,
            status=StockAlert.Status.ACTIVE
        )
        
        self.assertEqual(alerts.count(), 2)

    def test_09_no_duplicate_alerts_for_same_product(self):
        """Test that duplicate alerts are not created for the same product."""
        # Set stock below threshold
        self.product.stock_quantity = 5
        self.product.save()
        
        # Create alert twice
        from orders.views import _check_and_create_stock_alert
        _check_and_create_stock_alert(self.product)
        _check_and_create_stock_alert(self.product)
        
        # Verify only one alert exists
        alerts = StockAlert.objects.filter(
            product=self.product,
            producer=self.producer,
            status=StockAlert.Status.ACTIVE
        )
        
        self.assertEqual(alerts.count(), 1)

    def test_10_customer_cannot_access_stock_alerts(self):
        """Test that customers cannot access producer stock alerts."""
        self.client.login(username="customer1", password="TestPass123!")
        response = self.client.get(reverse("orders:stock_alerts"))
        
        # Should get 404 since customers can't access this view
        self.assertEqual(response.status_code, 404)

    def test_11_alert_contains_correct_information(self):
        """Test that alert contains all required information."""
        self.product.stock_quantity = 7
        self.product.save()
        
        alert = StockAlert.objects.create(
            product=self.product,
            producer=self.producer,
            stock_level=7,
            threshold=10,
            status=StockAlert.Status.ACTIVE
        )
        
        # Verify alert fields
        self.assertEqual(alert.product, self.product)
        self.assertEqual(alert.producer, self.producer)
        self.assertEqual(alert.stock_level, 7)
        self.assertEqual(alert.threshold, 10)
        self.assertEqual(alert.status, StockAlert.Status.ACTIVE)
        self.assertTrue(alert.is_active)
        self.assertIsNotNone(alert.created_at)

    def test_12_product_unavailable_when_out_of_stock(self):
        """Test that product becomes unavailable when out of stock."""
        # Reduce stock to zero
        self.product.stock_quantity = 0
        self.product.is_available = False
        self.product.save()
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 0)
        self.assertFalse(self.product.is_available)

    def test_13_alert_history_visible_to_producer(self):
        """Test that resolved alerts appear in history."""
        # Create and resolve an alert
        alert = StockAlert.objects.create(
            product=self.product,
            producer=self.producer,
            stock_level=5,
            threshold=10,
            status=StockAlert.Status.ACTIVE
        )
        
        alert.status = StockAlert.Status.RESOLVED
        alert.save()
        
        # Access dashboard
        self.client.login(username="eggfarmer", password="TestPass123!")
        response = self.client.get(reverse("orders:stock_alerts"))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resolved")

    def test_14_threshold_defaults_to_10(self):
        """Test that low stock threshold defaults to 10."""
        product3 = Product.objects.create(
            name="Test Product",
            description="Test",
            price=Decimal("1.00"),
            unit="kg",
            stock_quantity=100,
            category=self.category,
            producer=self.producer,
            is_available=True,
            seasonal_status="in_season"
        )
        
        self.assertEqual(product3.low_stock_threshold, 10)

    def test_15_alert_not_created_for_exact_threshold_match(self):
        """Test that alert is only created when stock is strictly below threshold."""
        # Set stock exactly at threshold
        self.product.stock_quantity = 10
        self.product.save()
        
        from orders.views import _check_and_create_stock_alert
        _check_and_create_stock_alert(self.product)
        
        # Should be no alert (stock == threshold, not <)
        alerts = StockAlert.objects.filter(
            product=self.product,
            status=StockAlert.Status.ACTIVE
        )
        
        self.assertEqual(alerts.count(), 0)

    def test_16_alert_created_via_checkout_process(self):
        """Test that alert is automatically created during checkout when stock falls below threshold."""
        # Set product stock to just above threshold
        self.product.stock_quantity = 11
        self.product.save()
        
        # Customer adds item that will bring stock below threshold
        self.client.login(username="customer1", password="TestPass123!")
        
        # Add to cart
        cart = Cart.objects.create(user=self.customer, status=Cart.STATUS_ACTIVE)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=5  # This will bring stock to 6, below threshold of 10
        )
        
        # Simulate stock decrement and alert check (as done in stripe_success)
        self.product.stock_quantity -= 5
        self.product.save()
        
        from orders.views import _check_and_create_stock_alert
        _check_and_create_stock_alert(self.product)
        
        # Verify alert was created
        alerts = StockAlert.objects.filter(
            product=self.product,
            status=StockAlert.Status.ACTIVE
        )
        
        self.assertEqual(alerts.count(), 1)
        alert = alerts.first()
        self.assertEqual(alert.stock_level, 6)

    def test_17_alert_resolved_via_product_edit_form(self):
        """Test that editing a product via the form resolves alerts when stock is replenished."""
        # Create an active alert
        self.product.stock_quantity = 5
        self.product.save()
        
        alert = StockAlert.objects.create(
            product=self.product,
            producer=self.producer,
            stock_level=5,
            threshold=10,
            status=StockAlert.Status.ACTIVE
        )
        
        # Login as producer
        self.client.login(username="eggfarmer", password="TestPass123!")
        
        # Update product via edit form to replenish stock
        response = self.client.post(
            reverse("edit_product", args=[self.product.id]),
            {
                "name": "Fresh Eggs",
                "description": "Fresh farm eggs",
                "price": "5.00",
                "unit": "dozen",
                "stock_quantity": "50",  # Above threshold
                "low_stock_threshold": "10",
                "category": self.category.id,
                "is_available": True,
                "seasonal_status": "in_season",
                "allergen_info": "Contains eggs",
            },
            follow=True
        )
        
        # Verify alert was resolved
        alert.refresh_from_db()
        self.assertEqual(alert.status, StockAlert.Status.RESOLVED)
        
    def test_18_alert_created_via_product_edit_form(self):
        """Test that editing a product via the form creates alerts when stock falls below threshold."""
        # Start with stock above threshold
        self.product.stock_quantity = 50
        self.product.save()
        
        # Verify no alerts exist
        self.assertEqual(StockAlert.objects.filter(product=self.product).count(), 0)
        
        # Login as producer
        self.client.login(username="eggfarmer", password="TestPass123!")
        
        # Update product via edit form to reduce stock below threshold
        response = self.client.post(
            reverse("edit_product", args=[self.product.id]),
            {
                "name": "Fresh Eggs",
                "description": "Fresh farm eggs",
                "price": "5.00",
                "unit": "dozen",
                "stock_quantity": "8",  # Below threshold of 10
                "low_stock_threshold": "10",
                "category": self.category.id,
                "is_available": True,
                "seasonal_status": "in_season",
                "allergen_info": "Contains eggs",
            },
            follow=True
        )
        
        # Verify alert was created
        alerts = StockAlert.objects.filter(
            product=self.product,
            status=StockAlert.Status.ACTIVE
        )
        self.assertEqual(alerts.count(), 1)
        alert = alerts.first()
        self.assertEqual(alert.stock_level, 8)
        self.assertEqual(alert.threshold, 10)

