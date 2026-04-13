from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from accounts.models import CustomUser
from marketplace.models import Product, Category
from orders.models import Order, OrderItem, Cart, CartItem


class TC021OrderHistoryTest(TestCase):
    """
    TC-021: As a customer, I want to view my order history so that I can reorder 
    favourite products and track past purchases.
    """
    
    def setUp(self):
        """
        Preconditions:
        - Customer is logged in
        - Customer has completed at least 3 orders in the past
        - Orders include various products and producers
        """
        self.client = Client()
        
        # Create customer user
        self.customer = CustomUser.objects.create_user(
            username='testcustomer',
            email='customer@test.com',
            password='CustomerPass123!',
            role=CustomUser.Role.CUSTOMER,
            first_name='John',
            last_name='Doe',
            postcode='BS1 4DJ',
            delivery_address='123 Test Street'
        )
        
        # Create producer 1
        self.producer1 = CustomUser.objects.create_user(
            username='organicfarm',
            email='producer1@organicfarm.com',
            password='ProducerPass123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Sarah',
            last_name='Green',
            postcode='BS2 8QA'
        )
        
        # Create producer 2
        self.producer2 = CustomUser.objects.create_user(
            username='localfarm',
            email='producer2@localfarm.com',
            password='ProducerPass123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Michael',
            last_name='Brown',
            postcode='BS3 4TG'
        )
        
        # Create categories
        self.vegetables_category = Category.objects.create(
            name='Vegetables',
            slug='vegetables',
            description='Fresh local vegetables',
            is_active=True
        )
        
        self.dairy_category = Category.objects.create(
            name='Dairy Products',
            slug='dairy-products',
            description='Fresh dairy products',
            is_active=True
        )
        
        # Create products from producer 1
        self.product1 = Product.objects.create(
            producer=self.producer1,
            category=self.vegetables_category,
            name='Organic Tomatoes',
            description='Fresh organic tomatoes',
            price=Decimal('3.50'),
            unit=Product.Unit.KG,
            stock_quantity=30,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
        )
        
        self.product2 = Product.objects.create(
            producer=self.producer1,
            category=self.vegetables_category,
            name='Organic Carrots',
            description='Fresh organic carrots',
            price=Decimal('2.50'),
            unit=Product.Unit.KG,
            stock_quantity=40,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.ALL_YEAR,
        )
        
        # Create products from producer 2
        self.product3 = Product.objects.create(
            producer=self.producer2,
            category=self.dairy_category,
            name='Fresh Milk',
            description='Fresh organic milk',
            price=Decimal('3.00'),
            unit=Product.Unit.L,
            stock_quantity=25,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.ALL_YEAR,
        )
        
        self.product4 = Product.objects.create(
            producer=self.producer2,
            category=self.vegetables_category,
            name='Local Lettuce',
            description='Green lettuce freshly harvested',
            price=Decimal('2.00'),
            unit=Product.Unit.ITEM,
            stock_quantity=15,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
        )
        
        # Create a product that will become unavailable for testing
        self.product5 = Product.objects.create(
            producer=self.producer1,
            category=self.vegetables_category,
            name='Seasonal Berries',
            description='Fresh seasonal berries',
            price=Decimal('5.00'),
            unit=Product.Unit.PACK,
            stock_quantity=0,
            is_available=True,  # Will be set to False later
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
        )
        
        # Create 3 past orders with different dates and statuses
        # Order 1: Oldest, delivered
        self.order1 = Order.objects.create(
            user=self.customer,
            status=Order.STATUS_DELIVERED,
            total=Decimal('12.00'),
            delivery_date=date.today() - timedelta(days=20),
            commission=Decimal('0.60'),
            full_name='John Doe',
            email='customer@test.com',
            address_line1='123 Test Street',
            address_line2='',
            city='Bristol',
            postcode='BS1 4DJ',
        )
        # Manually set created_at to be in the past
        self.order1.created_at = timezone.now() - timedelta(days=25)
        self.order1.save()
        
        OrderItem.objects.create(
            order=self.order1,
            product=self.product1,
            product_name=self.product1.name,
            unit_price=Decimal('3.50'),
            quantity=2,
            line_total=Decimal('7.00')
        )
        
        OrderItem.objects.create(
            order=self.order1,
            product=self.product5,
            product_name=self.product5.name,
            unit_price=Decimal('5.00'),
            quantity=1,
            line_total=Decimal('5.00')
        )
        
        # Order 2: Middle order, confirmed
        self.order2 = Order.objects.create(
            user=self.customer,
            status=Order.STATUS_CONFIRMED,
            total=Decimal('15.50'),
            delivery_date=date.today() + timedelta(days=2),
            commission=Decimal('0.78'),
            full_name='John Doe',
            email='customer@test.com',
            address_line1='123 Test Street',
            address_line2='',
            city='Bristol',
            postcode='BS1 4DJ',
        )
        self.order2.created_at = timezone.now() - timedelta(days=10)
        self.order2.save()
        
        OrderItem.objects.create(
            order=self.order2,
            product=self.product2,
            product_name=self.product2.name,
            unit_price=Decimal('2.50'),
            quantity=2,
            line_total=Decimal('5.00')
        )
        
        OrderItem.objects.create(
            order=self.order2,
            product=self.product3,
            product_name=self.product3.name,
            unit_price=Decimal('3.00'),
            quantity=2,
            line_total=Decimal('6.00')
        )
        
        OrderItem.objects.create(
            order=self.order2,
            product=self.product4,
            product_name=self.product4.name,
            unit_price=Decimal('2.00'),
            quantity=2,
            line_total=Decimal('4.00')
        )
        
        # Order 3: Most recent, delivered
        self.order3 = Order.objects.create(
            user=self.customer,
            status=Order.STATUS_DELIVERED,
            total=Decimal('9.50'),
            delivery_date=date.today() - timedelta(days=2),
            commission=Decimal('0.48'),
            full_name='John Doe',
            email='customer@test.com',
            address_line1='123 Test Street',
            address_line2='',
            city='Bristol',
            postcode='BS1 4DJ',
        )
        self.order3.created_at = timezone.now() - timedelta(days=3)
        self.order3.save()
        
        OrderItem.objects.create(
            order=self.order3,
            product=self.product1,
            product_name=self.product1.name,
            unit_price=Decimal('3.50'),
            quantity=1,
            line_total=Decimal('3.50')
        )
        
        OrderItem.objects.create(
            order=self.order3,
            product=self.product3,
            product_name=self.product3.name,
            unit_price=Decimal('3.00'),
            quantity=2,
            line_total=Decimal('6.00')
        )
        
        # Login the customer
        self.client.login(username='testcustomer', password='CustomerPass123!')
        
        self.order_list_url = reverse('orders:order_list')
        self.order_detail_url_1 = reverse('orders:order_detail', kwargs={'order_id': self.order1.id})
        self.order_detail_url_3 = reverse('orders:order_detail', kwargs={'order_id': self.order3.id})
        self.reorder_url_1 = reverse('orders:reorder', kwargs={'order_id': self.order1.id})
        self.reorder_url_3 = reverse('orders:reorder', kwargs={'order_id': self.order3.id})
        self.download_receipt_url_1 = reverse('orders:download_receipt', kwargs={'order_id': self.order1.id})
    
    def test_order_history_accessible(self):
        """
        Test Step 1: Navigate to 'My Account' or 'Order History'
        Expected: Order history is accessible
        """
        response = self.client.get(self.order_list_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_list.html')
    
    def test_orders_sorted_by_date(self):
        """
        Test Step 2: View list of past orders sorted by date (most recent first)
        Expected: Orders are sorted chronologically (most recent first)
        """
        response = self.client.get(self.order_list_url)
        
        orders = response.context['orders']
        order_ids = [order.id for order in orders]
        
        # Most recent order should be first
        self.assertEqual(order_ids[0], self.order3.id)
        self.assertEqual(order_ids[1], self.order2.id)
        self.assertEqual(order_ids[2], self.order1.id)
    
    def test_order_list_displays_required_info(self):
        """
        Test Step 3: Observe each order displays: order number, order date, 
        delivery date, producer names, total amount, order status
        Expected: All required information is displayed
        """
        response = self.client.get(self.order_list_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that order numbers are displayed
        self.assertContains(response, f'Order #{self.order1.id}')
        self.assertContains(response, f'Order #{self.order2.id}')
        self.assertContains(response, f'Order #{self.order3.id}')
        
        # Check that totals are displayed
        self.assertContains(response, '£12.00')
        self.assertContains(response, '£15.50')
        self.assertContains(response, '£9.50')
        
        # Check that status is displayed
        self.assertContains(response, 'Delivered')
        self.assertContains(response, 'Confirmed')
        
        # Check that producer names are shown
        orders = response.context['orders']
        for order in orders:
            self.assertIsNotNone(order.producer_names)
    
    def test_order_detail_accessible(self):
        """
        Test Step 4: Click on a completed order to view full details
        Expected: Full order details are retrievable
        """
        response = self.client.get(self.order_detail_url_1)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_detail.html')
        
        order = response.context['order']
        self.assertEqual(order.id, self.order1.id)
    
    def test_order_detail_shows_itemised_list(self):
        """
        Test Step 5: View itemised list of products with quantities and prices
        Expected: Order details match original purchase information
        """
        response = self.client.get(self.order_detail_url_1)
        
        items = response.context['items']
        
        # Verify correct number of items
        self.assertEqual(items.count(), 2)
        
        # Verify items contain correct information
        item_names = [item.product_name for item in items]
        self.assertIn('Organic Tomatoes', item_names)
        self.assertIn('Seasonal Berries', item_names)
        
        # Check line totals and quantities
        for item in items:
            if item.product_name == 'Organic Tomatoes':
                self.assertEqual(item.quantity, 2)
                self.assertEqual(item.line_total, Decimal('7.00'))
    
    def test_order_detail_shows_delivery_and_payment(self):
        """
        Test Step 6: View delivery address and payment information (partially masked)
        Expected: Payment information is secure and appropriately masked
        """
        response = self.client.get(self.order_detail_url_1)
        
        # Check delivery address is displayed
        self.assertContains(response, 'John Doe')
        self.assertContains(response, '123 Test Street')
        self.assertContains(response, 'Bristol')
        self.assertContains(response, 'BS1 4DJ')
        
        # Check payment information is displayed but masked
        self.assertContains(response, 'Payment Information')
        self.assertContains(response, '••••')  # Masked card number
        self.assertContains(response, 'Paid')
    
    def test_multi_vendor_orders_show_producer_breakdown(self):
        """
        Expected: Multi-vendor orders show producer breakdown
        """
        response = self.client.get(self.order_detail_url_3)
        
        grouped_items = response.context['grouped_items']
        
        # Order 3 has items from 2 producers
        self.assertEqual(len(grouped_items), 2)
        
        # Check that producers are distinctly shown
        producer_names = [group['producer'].username for group in grouped_items if group['producer']]
        self.assertIn('organicfarm', producer_names)
        self.assertIn('localfarm', producer_names)
    
    def test_reorder_button_present_for_delivered_orders(self):
        """
        Test Step 7: Click 'Reorder' button on a previous order
        Expected: Reorder function is available for delivered orders
        """
        response = self.client.get(self.order_detail_url_3)
        
        # Check that reorder button is present
        self.assertContains(response, 'Reorder')
        self.assertContains(response, f'/orders/my-orders/{self.order3.id}/reorder/')
    
    def test_reorder_adds_items_to_cart(self):
        """
        Test Step 8: Observe items are added to current cart
        Expected: Reorder function simplifies repeat purchases
        """
        # Ensure cart is empty before reorder
        cart = Cart.objects.filter(user=self.customer, status=Cart.STATUS_ACTIVE).first()
        if cart:
            CartItem.objects.filter(cart=cart).delete()
        
        # Perform reorder
        response = self.client.post(self.reorder_url_3, follow=True)
        
        # Verify redirect to cart
        self.assertRedirects(response, reverse('orders:cart'))
        
        # Check that items were added to cart
        cart = Cart.objects.get(user=self.customer, status=Cart.STATUS_ACTIVE)
        cart_items = CartItem.objects.filter(cart=cart)
        
        self.assertEqual(cart_items.count(), 2)
        
        # Verify correct products and quantities
        product_ids = [item.product.id for item in cart_items]
        self.assertIn(self.product1.id, product_ids)
        self.assertIn(self.product3.id, product_ids)
    
    def test_reorder_checks_product_availability(self):
        """
        Test Step 9: Verify product availability is checked
        Expected: Unavailable products in reorder are flagged
        """
        # Make product5 unavailable
        self.product5.is_available = False
        self.product5.save()
        
        # Clear cart
        cart = Cart.objects.filter(user=self.customer, status=Cart.STATUS_ACTIVE).first()
        if cart:
            CartItem.objects.filter(cart=cart).delete()
        
        # Attempt to reorder order1 which contains unavailable product5
        response = self.client.post(self.reorder_url_1, follow=True)
        
        # Check that a warning message was shown about unavailable products
        messages = list(response.context['messages'])
        warning_found = False
        for message in messages:
            if 'no longer available' in str(message).lower():
                warning_found = True
                self.assertIn('Seasonal Berries', str(message))
        
        self.assertTrue(warning_found, "Expected warning message about unavailable products")
        
        # Check that available product was still added
        cart = Cart.objects.get(user=self.customer, status=Cart.STATUS_ACTIVE)
        cart_items = CartItem.objects.filter(cart=cart)
        
        # Should have 1 item (only the available product)
        self.assertEqual(cart_items.count(), 1)
        
        # Verify it's the available product
        self.assertEqual(cart_items.first().product.id, self.product1.id)
    
    def test_download_order_receipt(self):
        """
        Expected: Can download order receipts for past purchases
        """
        response = self.client.get(self.download_receipt_url_1)
        
        # Check that response is a CSV file
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn(f'order_{self.order1.id}_receipt.csv', response['Content-Disposition'])
        
        # Verify CSV content contains order information
        content = response.content.decode('utf-8')
        self.assertIn('Bristol Regional Food Network', content)
        self.assertIn('Order Receipt', content)
        self.assertIn(str(self.order1.id), content)
        self.assertIn('Organic Tomatoes', content)
        self.assertIn('John Doe', content)
    
    def test_order_history_permanent_accessibility(self):
        """
        Acceptance Criteria: All historical orders are permanently accessible
        """
        response = self.client.get(self.order_list_url)
        
        orders = response.context['orders']
        
        # All 3 orders should be accessible
        self.assertEqual(orders.count(), 3)
        
        # Verify each order is accessible via detail view
        for order in orders:
            detail_url = reverse('orders:order_detail', kwargs={'order_id': order.id})
            detail_response = self.client.get(detail_url)
            self.assertEqual(detail_response.status_code, 200)
    
    def test_order_status_clearly_indicated(self):
        """
        Expected: Order status is clearly indicated
        """
        response = self.client.get(self.order_list_url)
        
        # Check that different statuses are displayed
        self.assertContains(response, 'Delivered')
        self.assertContains(response, 'Confirmed')
    
    def test_reorder_handles_quantity_adjustments(self):
        """
        Test Step 10-11: Adjust quantities if needed, proceed to checkout
        Expected: Customer can adjust quantities in cart after reorder
        """
        # Clear cart
        cart = Cart.objects.filter(user=self.customer, status=Cart.STATUS_ACTIVE).first()
        if cart:
            CartItem.objects.filter(cart=cart).delete()
        
        # Reorder
        response = self.client.post(self.reorder_url_3)
        
        # Get cart items
        cart = Cart.objects.get(user=self.customer, status=Cart.STATUS_ACTIVE)
        cart_items = CartItem.objects.filter(cart=cart)
        
        # Verify items can be updated (update one item quantity)
        item_to_update = cart_items.first()
        original_quantity = item_to_update.quantity
        
        update_url = reverse('orders:update_cart_item', kwargs={'item_id': item_to_update.id})
        update_response = self.client.post(update_url, {'quantity': original_quantity + 2})
        
        # Verify quantity was updated
        item_to_update.refresh_from_db()
        self.assertEqual(item_to_update.quantity, original_quantity + 2)
    
    def test_unauthorised_access_to_other_user_orders(self):
        """
        Security test: Verify users can only access their own orders
        """
        # Create another customer
        other_customer = CustomUser.objects.create_user(
            username='othercustomer',
            email='other@test.com',
            password='OtherPass123!',
            role=CustomUser.Role.CUSTOMER
        )
        
        # Logout current customer and login as other customer
        self.client.logout()
        self.client.login(username='othercustomer', password='OtherPass123!')
        
        # Try to access first customer's order
        response = self.client.get(self.order_detail_url_1)
        
        # Should get 404 or redirect, not access to the order
        self.assertEqual(response.status_code, 404)
    
    def test_reorder_only_works_with_post(self):
        """
        Security test: Reorder should only work with POST request
        """
        # Try GET request on reorder endpoint
        response = self.client.get(self.reorder_url_3)
        
        # Should redirect, not process reorder
        self.assertEqual(response.status_code, 302)
