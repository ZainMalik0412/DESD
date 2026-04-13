"""
Test Case ID: TC-002
User Story: As a customer, I want to register for an account so that I can browse and purchase local products.
Stakeholder: Customer (Young Professional/Family)
Priority: Critical

Description:
Validates that customers can successfully create accounts with personal information and 
delivery address details for purchasing purposes.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import authenticate
from accounts.models import CustomUser
from accounts.forms import CustomerRegistrationForm


class TC002CustomerRegistrationTest(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.registration_url = reverse('register')
        
        self.customer_data = {
            'username': 'robertjohnson',
            'first_name': 'Robert',
            'last_name': 'Johnson',
            'email': 'robert.johnson@email.com',
            'phone': '07700 900123',
            'delivery_address': '45 Park Street, Bristol',
            'postcode': 'BS1 5JG',
            'password': 'SecureP@ssw0rd123',
            'password_confirm': 'SecureP@ssw0rd123',
            'role': CustomUser.Role.CUSTOMER,
            'accept_terms': True,
        }
    
    def test_customer_registration_form_valid(self):
        form = CustomerRegistrationForm(data=self.customer_data)
        self.assertTrue(
            form.is_valid(),
            f"Form should be valid with correct customer data. Errors: {form.errors}"
        )
    
    def test_customer_account_creation(self):
        initial_user_count = CustomUser.objects.count()
        
        # Submit registration form
        response = self.client.post(self.registration_url, data=self.customer_data)
        
        self.assertEqual(
            CustomUser.objects.count(),
            initial_user_count + 1,
            "A new customer account should be created"
        )
        
        user = CustomUser.objects.get(email=self.customer_data['email'])
        
        self.assertIsNotNone(user, "Customer account should exist in the system")
        
        self.assertEqual(
            user.role,
            CustomUser.Role.CUSTOMER,
            "User should have customer role assigned"
        )
        
        self.assertEqual(
            user.get_role_display(),
            "Customer",
            "User role display should be 'Customer'"
        )
    
    def test_customer_personal_information_stored(self):
        form = CustomerRegistrationForm(data=self.customer_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        
        self.assertEqual(user.first_name, 'Robert')
        self.assertEqual(user.last_name, 'Johnson')
        self.assertEqual(user.email, 'robert.johnson@email.com')
        self.assertEqual(user.phone, '07700 900123')
        self.assertEqual(user.username, 'robertjohnson')
        
        self.assertNotEqual(
            user.password,
            self.customer_data['password'],
            "Password should not be stored in plain text"
        )
        
        # Check password is hashed (supports Argon2, PBKDF2, etc.)
        self.assertTrue(
            user.password.startswith(('argon2$', 'pbkdf2_sha256$')),
            "Password should be hashed using Django's password hasher (Argon2 or PBKDF2)"
        )
    
    def test_delivery_address_stored(self):
        form = CustomerRegistrationForm(data=self.customer_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        
        self.assertEqual(
            user.delivery_address,
            '45 Park Street, Bristol',
            "Delivery address should be saved correctly"
        )
        
        self.assertEqual(
            user.postcode,
            'BS1 5JG',
            "Postcode should be saved correctly"
        )
        
        user.refresh_from_db()
        self.assertEqual(user.delivery_address, '45 Park Street, Bristol')
        self.assertEqual(user.postcode, 'BS1 5JG')
    
    def test_customer_authentication(self):
        form = CustomerRegistrationForm(data=self.customer_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        
        authenticated_user = authenticate(
            username=self.customer_data['username'],
            password=self.customer_data['password']
        )
        
        self.assertIsNotNone(
            authenticated_user,
            "Customer should be able to authenticate with username and password"
        )
        
        self.assertEqual(
            authenticated_user.id,
            user.id,
            "Authenticated user should match the created user"
        )
        
        self.assertEqual(
            authenticated_user.role,
            CustomUser.Role.CUSTOMER,
            "Authenticated user should have customer role"
        )
    
    def test_customer_role_and_permissions(self):
        form = CustomerRegistrationForm(data=self.customer_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        
        user.refresh_from_db()
        
        self.assertEqual(
            user.role,
            CustomUser.Role.CUSTOMER,
            "User role should be CUSTOMER"
        )
        
        self.assertNotEqual(user.role, CustomUser.Role.PRODUCER)
        self.assertNotEqual(user.role, CustomUser.Role.COMMUNITY_GROUP)
        self.assertNotEqual(user.role, CustomUser.Role.RESTAURANT)
        self.assertNotEqual(user.role, CustomUser.Role.ADMIN)
    
    def test_customer_profile_complete(self):
        form = CustomerRegistrationForm(data=self.customer_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        
        profile = CustomUser.objects.get(username=self.customer_data['username'])
        
        self.assertEqual(profile.username, 'robertjohnson')
        self.assertEqual(profile.email, 'robert.johnson@email.com')
        self.assertEqual(profile.first_name, 'Robert')
        self.assertEqual(profile.last_name, 'Johnson')
        self.assertEqual(profile.phone, '07700 900123')
        self.assertEqual(profile.delivery_address, '45 Park Street, Bristol')
        self.assertEqual(profile.postcode, 'BS1 5JG')
        self.assertEqual(profile.role, CustomUser.Role.CUSTOMER)
    
    def test_terms_and_conditions_required(self):
        invalid_data = self.customer_data.copy()
        invalid_data['accept_terms'] = False
        
        form = CustomerRegistrationForm(data=invalid_data)
        self.assertFalse(
            form.is_valid(),
            "Form should be invalid when terms are not accepted"
        )
        self.assertIn(
            'accept_terms',
            form.errors,
            "Form should have an error for the accept_terms field"
        )
    
    def test_duplicate_email_rejected(self):
        form1 = CustomerRegistrationForm(data=self.customer_data)
        self.assertTrue(form1.is_valid())
        form1.save()
        
        duplicate_data = self.customer_data.copy()
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
        invalid_data = self.customer_data.copy()
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
    
    def test_invalid_postcode_rejected(self):
        invalid_data = self.customer_data.copy()
        invalid_data['postcode'] = 'INVALID'
        
        form = CustomerRegistrationForm(data=invalid_data)
        self.assertFalse(
            form.is_valid(),
            "Form should be invalid with invalid postcode"
        )
        self.assertIn(
            'postcode',
            form.errors,
            "Form should have an error for the postcode field"
        )
    
    def test_required_fields_validation(self):
        invalid_data = self.customer_data.copy()
        invalid_data['first_name'] = ''
        
        form = CustomerRegistrationForm(data=invalid_data)
        self.assertFalse(
            form.is_valid(),
            "Form should be invalid when first_name is missing"
        )
        
        invalid_data = self.customer_data.copy()
        invalid_data['last_name'] = ''
        
        form = CustomerRegistrationForm(data=invalid_data)
        self.assertFalse(
            form.is_valid(),
            "Form should be invalid when last_name is missing"
        )
        
        invalid_data = self.customer_data.copy()
        invalid_data['email'] = ''
        
        form = CustomerRegistrationForm(data=invalid_data)
        self.assertFalse(
            form.is_valid(),
            "Form should be invalid when email is missing"
        )
    
    def test_delivery_address_linked_to_profile(self):
        form = CustomerRegistrationForm(data=self.customer_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        
        customer = CustomUser.objects.get(username='robertjohnson')
        
        self.assertEqual(
            customer.delivery_address,
            '45 Park Street, Bristol',
            "Delivery address should be linked to customer profile"
        )
        
        self.assertEqual(
            customer.postcode,
            'BS1 5JG',
            "Postcode should be linked to customer profile"
        )
        
        self.assertEqual(customer.id, user.id)
