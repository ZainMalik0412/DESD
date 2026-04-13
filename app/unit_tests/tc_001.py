from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import authenticate
from accounts.models import CustomUser
from accounts.forms import CustomerRegistrationForm


class TC001ProducerRegistrationTest(TestCase):

    
    def setUp(self):

        self.client = Client()
        self.registration_url = reverse('register')
        
        # Test data from TC-001 specifications
        self.producer_data = {
            'username': 'bristolvalleyfarm',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane.smith@bristolvalleyfarm.com',
            'phone': '01179 123456',
            'delivery_address': 'Bristol Valley Farm, Rural Lane',
            'postcode': 'BS1 4DJ',
            'password': 'SecureP@ssw0rd123',
            'password_confirm': 'SecureP@ssw0rd123',
            'role': CustomUser.Role.PRODUCER,
            'accept_terms': True,
        }
    
    def test_producer_registration_form_valid(self):

        form = CustomerRegistrationForm(data=self.producer_data)
        self.assertTrue(
            form.is_valid(),
            f"Form should be valid with correct producer data. Errors: {form.errors}"
        )
    
    def test_producer_account_creation(self):

        initial_user_count = CustomUser.objects.count()
        
        response = self.client.post(self.registration_url, data=self.producer_data)
        
        self.assertEqual(
            CustomUser.objects.count(),
            initial_user_count + 1,
            "A new user account should be created"
        )
        
        user = CustomUser.objects.get(email=self.producer_data['email'])
        
        self.assertIsNotNone(user, "Producer account should exist in the system")
        
        self.assertEqual(
            user.role,
            CustomUser.Role.PRODUCER,
            "User should have producer role assigned"
        )
        
        self.assertEqual(
            user.get_role_display(),
            "Producer",
            "User role display should be 'Producer'"
        )
    
    def test_producer_business_information_saved(self):

        form = CustomerRegistrationForm(data=self.producer_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        
        self.assertEqual(user.first_name, 'Jane')
        self.assertEqual(user.last_name, 'Smith')
        self.assertEqual(user.email, 'jane.smith@bristolvalleyfarm.com')
        self.assertEqual(user.phone, '01179 123456')
        self.assertEqual(user.delivery_address, 'Bristol Valley Farm, Rural Lane')
        self.assertEqual(user.postcode, 'BS1 4DJ')
        self.assertEqual(user.username, 'bristolvalleyfarm')
    
    def test_password_securely_stored(self):
        form = CustomerRegistrationForm(data=self.producer_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        
        self.assertNotEqual(
            user.password,
            self.producer_data['password'],
            "Password should not be stored in plain text"
        )
        
        # Check password is hashed (supports Argon2, PBKDF2, etc.)
        self.assertTrue(
            user.password.startswith(('argon2$', 'pbkdf2_sha256$')),
            "Password should be hashed using Django's password hasher (Argon2 or PBKDF2)"
        )
        
        self.assertTrue(
            user.check_password(self.producer_data['password']),
            "User should be able to verify password using check_password method"
        )
    
    def test_producer_authentication(self):

        form = CustomerRegistrationForm(data=self.producer_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        
        authenticated_user = authenticate(
            username=self.producer_data['username'],
            password=self.producer_data['password']
        )
        
        self.assertIsNotNone(
            authenticated_user,
            "Producer should be able to authenticate with username and password"
        )
        
        self.assertEqual(
            authenticated_user.id,
            user.id,
            "Authenticated user should match the created user"
        )
        
        self.assertEqual(
            authenticated_user.role,
            CustomUser.Role.PRODUCER,
            "Authenticated user should have producer role"
        )
    
    def test_producer_profile_accessible(self):

        form = CustomerRegistrationForm(data=self.producer_data)
        self.assertTrue(form.is_valid())
        user = form.save()

        profile = CustomUser.objects.get(username=self.producer_data['username'])
        
        self.assertEqual(profile.username, 'bristolvalleyfarm')
        self.assertEqual(profile.email, 'jane.smith@bristolvalleyfarm.com')
        self.assertEqual(profile.first_name, 'Jane')
        self.assertEqual(profile.last_name, 'Smith')
        self.assertEqual(profile.phone, '01179 123456')
        self.assertEqual(profile.delivery_address, 'Bristol Valley Farm, Rural Lane')
        self.assertEqual(profile.postcode, 'BS1 4DJ')
        self.assertEqual(profile.role, CustomUser.Role.PRODUCER)
    
    def test_duplicate_email_rejected(self):

        form1 = CustomerRegistrationForm(data=self.producer_data)
        self.assertTrue(form1.is_valid())
        form1.save()
        
        duplicate_data = self.producer_data.copy()
        duplicate_data['username'] = 'different_username'
        
        form2 = CustomerRegistrationForm(data=duplicate_data)
        self.assertFalse(
            form2.is_valid(),
            "Form should be invalid when using duplicate email"
        )
        self.assertIn(
            'email',
            form2.errors,
            "Form should have an error for the email field"
        )
    
    def test_password_mismatch_rejected(self):
        invalid_data = self.producer_data.copy()
        invalid_data['password_confirm'] = 'DifferentPassword123'
        
        form = CustomerRegistrationForm(data=invalid_data)
        self.assertFalse(
            form.is_valid(),
            "Form should be invalid when passwords don't match"
        )
        self.assertIn(
            'password_confirm',
            form.errors,
            "Form should have an error for the password_confirm field"
        )
    
    def test_producer_role_assigned_correctly(self):

        form = CustomerRegistrationForm(data=self.producer_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        
        user.refresh_from_db()
        
        self.assertEqual(
            user.role,
            CustomUser.Role.PRODUCER,
            "User role should be PRODUCER"
        )
        
        self.assertNotEqual(user.role, CustomUser.Role.CUSTOMER)
        self.assertNotEqual(user.role, CustomUser.Role.COMMUNITY_GROUP)
        self.assertNotEqual(user.role, CustomUser.Role.RESTAURANT)
        self.assertNotEqual(user.role, CustomUser.Role.ADMIN)