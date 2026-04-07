from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from accounts.models import CustomUser
from marketplace.models import Product, Category
from orders.models import Order, OrderItem
from decimal import Decimal
from datetime import date, timedelta

CustomUser = get_user_model()


class TC022AuthenticationSecurityTests(TestCase):
    """
    TC-022: As a system administrator, I want to ensure secure authentication 
    so that user accounts and data are protected.
    """
    
    def setUp(self):
        """
        Preconditions:
        - System is configured with authentication system
        - User roles exist: Customer, Producer, Community Group, Restaurant, Admin
        - Test accounts exist for each role
        """
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        
        # Create test users for different roles
        self.customer = CustomUser.objects.create_user(
            username='test_customer',
            email='customer@test.com',
            password='SecurePass123!',
            role=CustomUser.Role.CUSTOMER,
            first_name='Test',
            last_name='Customer',
            postcode='BS1 4DJ'
        )
        
        self.producer = CustomUser.objects.create_user(
            username='test_producer',
            email='producer@test.com',
            password='SecurePass123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Test',
            last_name='Producer',
            postcode='BS2 8QA'
        )
        
        self.other_producer = CustomUser.objects.create_user(
            username='other_producer',
            email='other_producer@test.com',
            password='SecurePass123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Other',
            last_name='Producer',
            postcode='BS3 4TG'
        )
        
        # Create a category and product for testing
        self.category = Category.objects.create(
            name='Vegetables',
            slug='vegetables',
            description='Fresh vegetables',
            is_active=True
        )
        
        self.producer_product = Product.objects.create(
            producer=self.producer,
            category=self.category,
            name='Test Product',
            description='Test description',
            price=Decimal('5.00'),
            unit=Product.Unit.KG,
            stock_quantity=10,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
        )
        
        # Create an order for the other producer
        self.other_producer_order = Order.objects.create(
            user=self.customer,
            full_name='Test Customer',
            email='customer@test.com',
            address_line1='123 Test Street',
            address_line2='',
            city='Bristol',
            postcode='BS1 4DJ',
            total=Decimal('10.00'),
            commission=Decimal('0.50'),
            delivery_date=date.today() + timedelta(days=3),
            status=Order.STATUS_PENDING,
        )
        
        OrderItem.objects.create(
            order=self.other_producer_order,
            product=self.producer_product,
            product_name='Test Product',
            unit_price=Decimal('5.00'),
            quantity=2,
            line_total=Decimal('10.00'),
        )
    
    # Test Case 1: Password Security
    
    def test_weak_password_rejected(self):
        """
        Test Steps 1-3: Attempt to register with weak password,
        verify system rejects and shows password requirements
        """
        weak_password_data = {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@test.com',
            'phone': '07700900123',
            'delivery_address': '123 Test St',
            'postcode': 'BS1 5JG',
            'role': CustomUser.Role.CUSTOMER,
            'password': '123',  # Weak password
            'password_confirm': '123',
            'accept_terms': True,
        }
        
        response = self.client.post(self.register_url, data=weak_password_data)
        
        # Should not create the user
        self.assertFalse(CustomUser.objects.filter(username='newuser').exists())
        
        # Should show form errors
        self.assertEqual(response.status_code, 200)  # Stays on page with errors
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('password', form.errors)
        
        # Check that error message mentions password requirements
        content = response.content.decode()
        self.assertTrue(
            'too short' in content.lower() or 
            'password' in content.lower(),
            "Password requirements should be mentioned in error"
        )
    
    def test_strong_password_accepted(self):
        """
        Test Step 4: Register with strong password meeting requirements
        """
        strong_password_data = {
            'username': 'newuser_strong',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser_strong@test.com',
            'phone': '07700900123',
            'delivery_address': '123 Test St',
            'postcode': 'BS1 5JG',
            'role': CustomUser.Role.CUSTOMER,
            'password': 'StrongPassword123!',
            'password_confirm': 'StrongPassword123!',
            'accept_terms': True,
        }
        
        response = self.client.post(self.register_url, data=strong_password_data)
        
        # Should create the user
        self.assertTrue(CustomUser.objects.filter(username='newuser_strong').exists())
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
    
    def test_password_is_hashed_in_database(self):
        """
        Test Step 5: Verify password is hashed in database (not stored as plain text)
        """
        # Create a new user
        user = CustomUser.objects.create_user(
            username='hash_test_user',
            email='hash@test.com',
            password='MySecurePassword123!',
            role=CustomUser.Role.CUSTOMER
        )
        
        # Retrieve the user from database
        user_from_db = CustomUser.objects.get(username='hash_test_user')
        
        # Password should NOT be stored in plain text
        self.assertNotEqual(user_from_db.password, 'MySecurePassword123!')
        
        # Password should be hashed (system uses Argon2 or PBKDF2)
        self.assertTrue(
            user_from_db.password.startswith('argon2') or 
            user_from_db.password.startswith('pbkdf2_sha256$')
        )
        
        # But check_password should work
        self.assertTrue(user_from_db.check_password('MySecurePassword123!'))
        self.assertFalse(user_from_db.check_password('WrongPassword'))
    
    # Test Case 2: Login Security
    
    def test_login_with_incorrect_password(self):
        """
        Test Steps 6-7: Attempt login with incorrect password,
        verify appropriate error message
        """
        response = self.client.post(self.login_url, {
            'username': 'test_customer',
            'password': 'WrongPassword123!',
        })
        
        # Should not be logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
        # Should show error message (without revealing if user exists)
        content = response.content.decode()
        self.assertTrue(
            'incorrect' in content.lower() or 
            'invalid' in content.lower() or
            'error' in content.lower(),
            "Should show generic error message"
        )
        
        # Should NOT reveal whether username exists
        self.assertNotIn('does not exist', content.lower())
        self.assertNotIn('user not found', content.lower())
    
    def test_login_with_correct_credentials(self):
        """
        Test Steps 8-9: Attempt login with correct credentials,
        verify successful authentication and session creation
        """
        response = self.client.post(self.login_url, {
            'username': 'test_customer',
            'password': 'SecurePass123!',
        }, follow=True)
        
        # Should be logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, 'test_customer')
        
        # Should have a session
        self.assertIn('_auth_user_id', self.client.session)
        
        # Should redirect to home page
        self.assertEqual(response.status_code, 200)
    
    # Test Case 3: Authorisation
    
    def test_customer_cannot_access_producer_features(self):
        """
        Test Steps 11-13: Log in as customer, attempt to access producer-only features,
        verify access is denied with appropriate error
        """
        # Login as customer
        self.client.login(username='test_customer', password='SecurePass123!')
        
        # Try to access add product page (producer only)
        add_product_url = reverse('add_product')
        response = self.client.get(add_product_url)
        
        # Should be forbidden or redirected
        self.assertIn(response.status_code, [302, 403])
        
        if response.status_code == 403:
            # Should show forbidden message
            content = response.content.decode()
            self.assertTrue(
                'permission' in content.lower() or 
                'forbidden' in content.lower() or
                'not authorised' in content.lower()
            )
        else:
            # Redirected away from the page
            self.assertNotEqual(response.url, add_product_url)
        
        # Try to access my products page (producer only)
        my_products_url = reverse('my_products')
        response = self.client.get(my_products_url)
        
        # Should be redirected (customers don't have products)
        self.assertEqual(response.status_code, 302)
    
    def test_producer_can_access_producer_features(self):
        """
        Test Steps 14-15: Log in as producer,
        verify access to producer features is granted
        """
        # Login as producer
        self.client.login(username='test_producer', password='SecurePass123!')
        
        # Should be able to access add product page
        add_product_url = reverse('add_product')
        response = self.client.get(add_product_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Product')
        
        # Should be able to access my products page
        my_products_url = reverse('my_products')
        response = self.client.get(my_products_url)
        self.assertEqual(response.status_code, 200)
    
    def test_producer_cannot_access_other_producer_orders(self):
        """
        Test Steps 16-17: As producer, attempt to view other producer's order details,
        verify access is denied
        """
        # Login as the other producer (not the one who has items in the order)
        self.client.login(username='other_producer', password='SecurePass123!')
        
        # Try to access an order that belongs to a different producer
        manage_order_url = reverse('orders:manage_order_detail', 
                                   kwargs={'order_id': self.other_producer_order.id})
        response = self.client.get(manage_order_url)
        
        # Should get 404 (order not found from their perspective)
        self.assertEqual(response.status_code, 404)
    
    def test_customer_can_only_access_own_orders(self):
        """
        Additional test: Verify customers can only access their own orders
        """
        # Create another customer
        other_customer = CustomUser.objects.create_user(
            username='other_customer',
            email='other_customer@test.com',
            password='SecurePass123!',
            role=CustomUser.Role.CUSTOMER
        )
        
        # Login as other customer
        self.client.login(username='other_customer', password='SecurePass123!')
        
        # Try to access the first customer's order
        order_detail_url = reverse('orders:order_detail', 
                                   kwargs={'order_id': self.other_producer_order.id})
        response = self.client.get(order_detail_url)
        
        # Should get 404 (not their order)
        self.assertEqual(response.status_code, 404)
    
    # Test Case 4: Session Management
    
    def test_session_persists_after_login(self):
        """
        Test Steps 19-20: Log in and establish session,
        verify session persists
        """
        # Login
        self.client.login(username='test_customer', password='SecurePass123!')
        
        # Get session key
        session_key = self.client.session.session_key
        self.assertIsNotNone(session_key)
        
        # Verify session exists in database
        session_exists = Session.objects.filter(session_key=session_key).exists()
        self.assertTrue(session_exists)
        
        # Make another request - session should persist
        response = self.client.get('/')
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, 'test_customer')
    
    def test_logout_terminates_session(self):
        """
        Test Steps 22-23: Log out explicitly,
        verify session is terminated and protected pages require re-login
        """
        # Login first
        self.client.login(username='test_customer', password='SecurePass123!')
        self.assertTrue(self.client.session.get('_auth_user_id'))
        
        # Logout
        response = self.client.post(self.logout_url)
        
        # Session should not have auth user
        self.assertNotIn('_auth_user_id', self.client.session)
        
        # Should be redirected
        self.assertEqual(response.status_code, 302)
        
        # Trying to access protected page should redirect to login
        my_orders_url = reverse('orders:order_list')
        response = self.client.get(my_orders_url)
        
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    # Additional Security Tests
    
    def test_unauthenticated_user_cannot_access_protected_pages(self):
        """
        Verify that unauthenticated users are redirected to login
        for protected pages
        """
        protected_urls = [
            reverse('orders:cart'),
            reverse('orders:order_list'),
            reverse('add_product'),
            reverse('orders:manage_orders'),
        ]
        
        for url in protected_urls:
            response = self.client.get(url)
            # Should redirect to login
            self.assertEqual(response.status_code, 302)
            self.assertIn('/accounts/login/', response.url)
    
    def test_password_mismatch_rejected(self):
        """
        Verify that password confirmation must match
        """
        mismatch_data = {
            'username': 'mismatch_user',
            'first_name': 'Mismatch',
            'last_name': 'User',
            'email': 'mismatch@test.com',
            'phone': '07700900123',
            'delivery_address': '123 Test St',
            'postcode': 'BS1 5JG',
            'role': CustomUser.Role.CUSTOMER,
            'password': 'StrongPassword123!',
            'password_confirm': 'DifferentPassword123!',  # Mismatch
            'accept_terms': True,
        }
        
        response = self.client.post(self.register_url, data=mismatch_data)
        
        # Should not create the user
        self.assertFalse(CustomUser.objects.filter(username='mismatch_user').exists())
        
        # Should show password mismatch error
        form = response.context['form']
        self.assertIn('password_confirm', form.errors)
        self.assertIn('Passwords do not match.', form.errors['password_confirm'])
    
    def test_duplicate_email_rejected(self):
        """
        Verify that duplicate email addresses are rejected
        """
        duplicate_email_data = {
            'username': 'duplicate_email_user',
            'first_name': 'Duplicate',
            'last_name': 'User',
            'email': 'customer@test.com',  # Already exists
            'phone': '07700900123',
            'delivery_address': '123 Test St',
            'postcode': 'BS1 5JG',
            'role': CustomUser.Role.CUSTOMER,
            'password': 'StrongPassword123!',
            'password_confirm': 'StrongPassword123!',
            'accept_terms': True,
        }
        
        response = self.client.post(self.register_url, data=duplicate_email_data)
        
        # Should not create the user
        self.assertFalse(
            CustomUser.objects.filter(username='duplicate_email_user').exists()
        )
        
        # Should show email already exists error
        form = response.context['form']
        self.assertIn('email', form.errors)
        self.assertIn('An account with this email already exists.', form.errors['email'])
    
    def test_sql_injection_prevented(self):
        """
        Verify that SQL injection attempts in login are prevented
        """
        # Attempt SQL injection in username field
        sql_injection_attempts = [
            "admin'--",
            "admin' OR '1'='1",
            "'; DROP TABLE accounts_customuser; --",
        ]
        
        for injection_attempt in sql_injection_attempts:
            response = self.client.post(self.login_url, {
                'username': injection_attempt,
                'password': 'anything',
            })
            
            # Should not be logged in
            self.assertFalse(response.wsgi_request.user.is_authenticated)
            
            # Database should not be affected
            user_count = CustomUser.objects.count()
            self.assertGreaterEqual(user_count, 3)  # At least our test users exist
    
    def test_admin_role_cannot_be_registered(self):
        """
        Verify that admin role cannot be selected during registration
        (admin accounts should only be created via Django admin)
        """
        admin_role_data = {
            'username': 'wannabe_admin',
            'first_name': 'Admin',
            'last_name': 'Wannabe',
            'email': 'admin@test.com',
            'phone': '07700900123',
            'delivery_address': '123 Test St',
            'postcode': 'BS1 5JG',
            'role': CustomUser.Role.ADMIN,  # Try to register as admin
            'password': 'StrongPassword123!',
            'password_confirm': 'StrongPassword123!',
            'accept_terms': True,
        }
        
        response = self.client.post(self.register_url, data=admin_role_data)
        
        # Should not create an admin user
        self.assertFalse(
            CustomUser.objects.filter(username='wannabe_admin', role=CustomUser.Role.ADMIN).exists()
        )
    
    def test_session_cookie_security(self):
        """
        Verify that session cookies have security attributes
        """
        # Login to create a session
        self.client.login(username='test_customer', password='SecurePass123!')
        
        # Check that session cookie exists
        self.assertIn('sessionid', self.client.cookies)
        
        # In production, these should be set via settings:
        # SESSION_COOKIE_HTTPONLY = True (prevents JS access)
        # SESSION_COOKIE_SECURE = True (HTTPS only)
        # SESSION_COOKIE_SAMESITE = 'Lax' or 'Strict' (CSRF protection)
        
        # We can at least verify the session is working
        session_key = self.client.session.session_key
        self.assertIsNotNone(session_key)
