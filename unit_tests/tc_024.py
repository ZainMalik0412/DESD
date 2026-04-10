from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from accounts.models import CustomUser
from marketplace.models import Product, Category, ProductReview
from marketplace.forms import ProductReviewForm
from orders.models import Order, OrderItem


class TC024ProductReviewTest(TestCase):
    """
    TC-024: As a customer, I want to rate and review products so that I can share 
    my experience and help other customers make informed decisions.
    
    Validates the review and rating system allowing customers to provide feedback 
    on purchased products, supporting community trust and quality assurance.
    """

    def setUp(self):
        """Set up test data including customer, producer, product, and delivered order."""
        self.client = Client()
        
        # Create producer user
        self.producer = CustomUser.objects.create_user(
            username='testproducer',
            email='producer@example.com',
            password='ProducerPass123',
            role=CustomUser.Role.PRODUCER,
            first_name='John',
            last_name='Farmer',
            postcode='BS1 4DJ'
        )
        
        # Create customer user
        self.customer = CustomUser.objects.create_user(
            username='testcustomer',
            email='customer@example.com',
            password='CustomerPass123',
            role=CustomUser.Role.CUSTOMER,
            first_name='Alice',
            last_name='Smith',
            postcode='BS2 8HQ'
        )
        
        # Create category
        self.category = Category.objects.create(
            name='Vegetables',
            slug='vegetables',
            is_active=True
        )
        
        # Create product: Organic Tomatoes
        self.product = Product.objects.create(
            category=self.category,
            producer=self.producer,
            name='Organic Tomatoes',
            description='Fresh organic tomatoes',
            price=3.50,
            unit='kg',
            stock_quantity=50,
            is_available=True
        )
        
        # Create a completed/delivered order with the product
        self.delivered_order = Order.objects.create(
            user=self.customer,
            status=Order.STATUS_DELIVERED,
            total=10.50,
            commission=0.53,
            full_name='Alice Smith',
            email='customer@example.com',
            address_line1='123 Test Street',
            city='Bristol',
            postcode='BS2 8HQ'
        )
        
        OrderItem.objects.create(
            order=self.delivered_order,
            product=self.product,
            product_name='Organic Tomatoes',
            unit_price=3.50,
            quantity=3,
            line_total=10.50
        )
        
        # Create a pending order (not yet delivered)
        self.pending_order = Order.objects.create(
            user=self.customer,
            status=Order.STATUS_PENDING,
            total=7.00,
            commission=0.35,
            full_name='Alice Smith',
            email='customer@example.com',
            address_line1='123 Test Street',
            city='Bristol',
            postcode='BS2 8HQ'
        )
        
        OrderItem.objects.create(
            order=self.pending_order,
            product=self.product,
            product_name='Organic Tomatoes',
            unit_price=3.50,
            quantity=2,
            line_total=7.00
        )
        
        # URLs
        self.submit_review_url = reverse('submit_review', kwargs={'product_id': self.product.id})
        self.product_detail_url = reverse('product_detail', kwargs={'product_id': self.product.id})
    
    def test_customer_can_access_review_form_for_delivered_product(self):
        """Test Step 1-4: Customer can access review form for purchased products."""
        self.client.login(username='testcustomer', password='CustomerPass123')
        response = self.client.get(self.submit_review_url)
        
        self.assertEqual(response.status_code, 200, "Review form should be accessible")
        self.assertContains(response, 'Write a Review', msg_prefix="Page should show review form")
        self.assertContains(response, 'Organic Tomatoes', msg_prefix="Page should show product name")
    
    def test_review_form_validation(self):
        """Test that the review form validates input correctly."""
        # Valid review data
        valid_data = {
            'rating': 5,
            'title': 'Excellent quality and flavour',
            'review_text': 'These tomatoes were incredibly fresh and flavourful. Perfect for our family\'s salads. Will definitely order again.',
            'is_anonymous': False
        }
        
        form = ProductReviewForm(data=valid_data)
        self.assertTrue(form.is_valid(), f"Form should be valid with correct data. Errors: {form.errors}")
    
    def test_customer_can_submit_review(self):
        """Test Steps 5-8: Customer can submit a review with rating and text."""
        self.client.login(username='testcustomer', password='CustomerPass123')
        
        review_data = {
            'rating': 5,
            'title': 'Excellent quality and flavour',
            'review_text': 'These tomatoes were incredibly fresh and flavourful. Perfect for our family\'s salads. Will definitely order again.',
            'is_anonymous': False
        }
        
        initial_review_count = ProductReview.objects.count()
        
        response = self.client.post(self.submit_review_url, data=review_data)
        
        # Should redirect to product detail after successful submission
        self.assertEqual(response.status_code, 302, "Should redirect after successful review submission")
        
        # Verify review was created
        self.assertEqual(
            ProductReview.objects.count(),
            initial_review_count + 1,
            "A new review should be created"
        )
        
        review = ProductReview.objects.get(product=self.product, customer=self.customer)
        self.assertEqual(review.rating, 5, "Rating should be saved correctly")
        self.assertEqual(review.title, 'Excellent quality and flavour', "Title should be saved correctly")
        self.assertIn('incredibly fresh', review.review_text, "Review text should be saved correctly")
        self.assertEqual(review.is_anonymous, False, "Anonymous flag should be saved correctly")
    
    def test_review_appears_on_product_page(self):
        """Test Steps 9-10: Review appears on product page."""
        # Create a review
        review = ProductReview.objects.create(
            product=self.product,
            customer=self.customer,
            order=self.delivered_order,
            rating=5,
            title='Excellent quality and flavour',
            review_text='These tomatoes were incredibly fresh and flavourful.',
            is_anonymous=False
        )
        
        # Visit product page
        response = self.client.get(self.product_detail_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Customer Reviews', msg_prefix="Page should have reviews section")
        self.assertContains(response, 'Excellent quality and flavour', msg_prefix="Review title should appear")
        self.assertContains(response, 'incredibly fresh', msg_prefix="Review text should appear")
    
    def test_average_rating_calculated(self):
        """Test Step 11: Average rating is calculated and displayed."""
        # Create multiple reviews with different ratings
        ProductReview.objects.create(
            product=self.product,
            customer=self.customer,
            order=self.delivered_order,
            rating=5,
            title='Excellent',
            review_text='Great product',
            is_anonymous=False
        )
        
        # Create another customer and order for second review
        customer2 = CustomUser.objects.create_user(
            username='customer2',
            email='customer2@example.com',
            password='Pass123',
            role=CustomUser.Role.CUSTOMER
        )
        
        order2 = Order.objects.create(
            user=customer2,
            status=Order.STATUS_DELIVERED,
            total=7.00,
            commission=0.35,
            full_name='Customer Two',
            email='customer2@example.com',
            address_line1='456 Test Ave',
            city='Bristol',
            postcode='BS3 1AA'
        )
        
        OrderItem.objects.create(
            order=order2,
            product=self.product,
            product_name='Organic Tomatoes',
            unit_price=3.50,
            quantity=2,
            line_total=7.00
        )
        
        ProductReview.objects.create(
            product=self.product,
            customer=customer2,
            order=order2,
            rating=4,
            title='Good',
            review_text='Nice tomatoes',
            is_anonymous=False
        )
        
        # Check average rating
        average_rating = self.product.get_average_rating()
        self.assertEqual(average_rating, 4.5, "Average rating should be (5+4)/2 = 4.5")
        
        # Check review count
        review_count = self.product.get_review_count()
        self.assertEqual(review_count, 2, "Should have 2 reviews")
    
    def test_review_shows_customer_name_and_date(self):
        """Test Step 12: Review shows customer name, date, and verified purchase badge."""
        review = ProductReview.objects.create(
            product=self.product,
            customer=self.customer,
            order=self.delivered_order,
            rating=5,
            title='Great product',
            review_text='Highly recommended',
            is_anonymous=False
        )
        
        response = self.client.get(self.product_detail_url)
        
        # Check for customer display name
        self.assertContains(response, review.display_name, msg_prefix="Customer name should be displayed")
        
        # Check for verified purchase badge
        self.assertContains(response, 'Verified Purchase', msg_prefix="Verified purchase badge should be shown")
    
    def test_anonymous_review_hides_customer_name(self):
        """Test that anonymous reviews hide customer name."""
        review = ProductReview.objects.create(
            product=self.product,
            customer=self.customer,
            order=self.delivered_order,
            rating=5,
            title='Great product',
            review_text='Highly recommended',
            is_anonymous=True
        )
        
        self.assertEqual(review.display_name, 'Anonymous', "Display name should be 'Anonymous'")
        
        response = self.client.get(self.product_detail_url)
        self.assertContains(response, 'Anonymous', msg_prefix="Should show 'Anonymous' for anonymous reviews")
    
    def test_cannot_review_product_from_pending_order(self):
        """Test Step 13-14: System prevents reviewing products from undelivered orders."""
        # Create a new customer who only has pending orders
        customer_pending = CustomUser.objects.create_user(
            username='customer_pending',
            email='pending@example.com',
            password='Pass123',
            role=CustomUser.Role.CUSTOMER
        )
        
        pending_only_order = Order.objects.create(
            user=customer_pending,
            status=Order.STATUS_PENDING,
            total=7.00,
            commission=0.35,
            full_name='Pending Customer',
            email='pending@example.com',
            address_line1='789 Pending St',
            city='Bristol',
            postcode='BS4 2BB'
        )
        
        OrderItem.objects.create(
            order=pending_only_order,
            product=self.product,
            product_name='Organic Tomatoes',
            unit_price=3.50,
            quantity=2,
            line_total=7.00
        )
        
        self.client.login(username='customer_pending', password='Pass123')
        response = self.client.get(self.submit_review_url)
        
        # Should show error message
        self.assertContains(
            response, 
            'delivered', 
            msg_prefix="Should show message about needing delivered order",
            status_code=200
        )
    
    def test_cannot_submit_duplicate_review(self):
        """Test Steps 15-16: System prevents duplicate reviews for same product."""
        # Create first review
        ProductReview.objects.create(
            product=self.product,
            customer=self.customer,
            order=self.delivered_order,
            rating=5,
            title='First review',
            review_text='Great product',
            is_anonymous=False
        )
        
        self.client.login(username='testcustomer', password='CustomerPass123')
        response = self.client.get(self.submit_review_url)
        
        # Should show error message about existing review
        self.assertContains(
            response,
            'already reviewed',
            msg_prefix="Should show message about existing review",
            status_code=200
        )
    
    def test_producer_can_respond_to_review(self):
        """Test that producers can respond to reviews on their products."""
        review = ProductReview.objects.create(
            product=self.product,
            customer=self.customer,
            order=self.delivered_order,
            rating=5,
            title='Great product',
            review_text='Highly recommended',
            is_anonymous=False
        )
        
        self.client.login(username='testproducer', password='ProducerPass123')
        
        respond_url = reverse('producer_respond_review', kwargs={'review_id': review.id})
        response_data = {
            'producer_response': 'Thank you for your feedback! We\'re glad you enjoyed our tomatoes.'
        }
        
        response = self.client.post(respond_url, data=response_data)
        
        # Should redirect after successful response
        self.assertEqual(response.status_code, 302, "Should redirect after posting response")
        
        # Verify response was saved
        review.refresh_from_db()
        self.assertIsNotNone(review.producer_response, "Producer response should be saved")
        self.assertIn('Thank you', review.producer_response, "Response text should be saved correctly")
        self.assertIsNotNone(review.producer_response_date, "Response date should be recorded")
    
    def test_customer_can_edit_own_review(self):
        """Test that customers can edit their own reviews."""
        review = ProductReview.objects.create(
            product=self.product,
            customer=self.customer,
            order=self.delivered_order,
            rating=4,
            title='Good product',
            review_text='Nice tomatoes',
            is_anonymous=False
        )
        
        self.client.login(username='testcustomer', password='CustomerPass123')
        
        edit_url = reverse('edit_review', kwargs={'review_id': review.id})
        updated_data = {
            'rating': 5,
            'title': 'Excellent product',
            'review_text': 'Amazing tomatoes, even better than I thought!',
            'is_anonymous': False
        }
        
        response = self.client.post(edit_url, data=updated_data)
        
        # Should redirect after successful edit
        self.assertEqual(response.status_code, 302, "Should redirect after editing review")
        
        # Verify review was updated
        review.refresh_from_db()
        self.assertEqual(review.rating, 5, "Rating should be updated")
        self.assertEqual(review.title, 'Excellent product', "Title should be updated")
        self.assertIn('Amazing', review.review_text, "Review text should be updated")
    
    def test_rating_validation(self):
        """Test that rating must be between 1 and 5 stars."""
        invalid_data = {
            'rating': 6,  # Invalid: outside range
            'title': 'Test',
            'review_text': 'Test review',
            'is_anonymous': False
        }
        
        form = ProductReviewForm(data=invalid_data)
        self.assertFalse(form.is_valid(), "Form should reject rating outside 1-5 range")
        self.assertIn('rating', form.errors, "Should have error for rating field")
    
    def test_review_text_required(self):
        """Test that review text is required."""
        invalid_data = {
            'rating': 5,
            'title': 'Test',
            'review_text': '',  # Empty review text
            'is_anonymous': False
        }
        
        form = ProductReviewForm(data=invalid_data)
        self.assertFalse(form.is_valid(), "Form should require review text")
        self.assertIn('review_text', form.errors, "Should have error for review_text field")
    
    def test_review_title_required(self):
        """Test that review title is required."""
        invalid_data = {
            'rating': 5,
            'title': '',  # Empty title
            'review_text': 'This is my review',
            'is_anonymous': False
        }
        
        form = ProductReviewForm(data=invalid_data)
        self.assertFalse(form.is_valid(), "Form should require review title")
        self.assertIn('title', form.errors, "Should have error for title field")
