from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from accounts.models import CustomUser
from marketplace.models import Product, Category
from marketplace.forms import ProductForm


class TC003ProductListingTest(TestCase):
    
    def setUp(self):
        self.client = Client()
        
        self.producer = CustomUser.objects.create_user(
            username='bristolvalleyfarm',
            email='producer@bristolvalley.com',
            password='ProducerPass123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Jane',
            last_name='Smith'
        )
        
        self.category = Category.objects.create(
            name='Dairy & Eggs',
            slug='dairy-eggs',
            description='Fresh dairy products and eggs',
            is_active=True
        )
        
        self.product_data = {
            'name': 'Organic Free Range Eggs',
            'category': self.category.id,
            'description': 'Fresh organic eggs from free-range hens, collected daily',
            'price': Decimal('3.50'),
            'unit': Product.Unit.DOZEN,
            'stock_quantity': 50,
            'is_available': True,
            'seasonal_status': Product.SeasonalStatus.IN_SEASON,
            'allergen_info': 'Contains eggs',
            'harvest_date': timezone.now().date(),
        }
        
        self.add_product_url = reverse('add_product')
        self.my_products_url = reverse('my_products')
        self.browse_url = reverse('browse')
    
    def test_product_form_valid(self):
        form = ProductForm(data=self.product_data)
        self.assertTrue(
            form.is_valid(),
            f"Form should be valid with correct product data. Errors: {form.errors}"
        )
    
    def test_product_creation(self):
        initial_product_count = Product.objects.count()
        
        self.client.login(username='bristolvalleyfarm', password='ProducerPass123!')
        
        response = self.client.post(self.add_product_url, data=self.product_data)
        
        self.assertEqual(
            Product.objects.count(),
            initial_product_count + 1,
            "A new product should be created"
        )
        
        product = Product.objects.get(name='Organic Free Range Eggs')
        
        self.assertIsNotNone(product, "Product should exist in the database")
        
        self.assertEqual(
            product.producer.id,
            self.producer.id,
            "Product should be linked to the authenticated producer"
        )
    
    def test_product_linked_to_producer(self):
        self.client.login(username='bristolvalleyfarm', password='ProducerPass123!')
        
        form = ProductForm(data=self.product_data)
        self.assertTrue(form.is_valid())
        product = form.save(commit=False)
        product.producer = self.producer
        product.save()
        
        self.assertEqual(
            product.producer.id,
            self.producer.id,
            "Product must be linked to the authenticated producer"
        )
        
        self.assertEqual(
            product.producer.username,
            'bristolvalleyfarm',
            "Product should be linked to correct producer username"
        )
    
    def test_all_product_fields_stored(self):
        form = ProductForm(data=self.product_data)
        self.assertTrue(form.is_valid())
        product = form.save(commit=False)
        product.producer = self.producer
        product.save()
        
        self.assertEqual(product.name, 'Organic Free Range Eggs')
        self.assertEqual(product.category.id, self.category.id)
        self.assertEqual(product.description, 'Fresh organic eggs from free-range hens, collected daily')
        self.assertEqual(product.price, Decimal('3.50'))
        self.assertEqual(product.unit, Product.Unit.DOZEN)
        self.assertEqual(product.stock_quantity, 50)
        self.assertTrue(product.is_available)
        self.assertEqual(product.seasonal_status, Product.SeasonalStatus.IN_SEASON)
        self.assertEqual(product.allergen_info, 'Contains eggs')
        self.assertEqual(product.harvest_date, timezone.now().date())
    
    def test_product_appears_in_producer_dashboard(self):
        self.client.login(username='bristolvalleyfarm', password='ProducerPass123!')
        
        Product.objects.create(
            producer=self.producer,
            category=self.category,
            name='Organic Free Range Eggs',
            description='Fresh organic eggs from free-range hens, collected daily',
            price=Decimal('3.50'),
            unit=Product.Unit.DOZEN,
            stock_quantity=50,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
            allergen_info='Contains eggs',
            harvest_date=timezone.now().date(),
        )
        
        response = self.client.get(self.my_products_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Organic Free Range Eggs')
    
    def test_product_visible_in_marketplace(self):
        Product.objects.create(
            producer=self.producer,
            category=self.category,
            name='Organic Free Range Eggs',
            description='Fresh organic eggs from free-range hens, collected daily',
            price=Decimal('3.50'),
            unit=Product.Unit.DOZEN,
            stock_quantity=50,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
            allergen_info='Contains eggs',
            harvest_date=timezone.now().date(),
        )
        
        response = self.client.get(self.browse_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Organic Free Range Eggs')
    
    def test_category_validation(self):
        form = ProductForm(data=self.product_data)
        self.assertTrue(form.is_valid())
        product = form.save(commit=False)
        product.producer = self.producer
        product.save()
        
        self.assertEqual(product.category.name, 'Dairy & Eggs')
        self.assertEqual(product.category.slug, 'dairy-eggs')
    
    def test_price_validation(self):
        form = ProductForm(data=self.product_data)
        self.assertTrue(form.is_valid())
        product = form.save(commit=False)
        product.producer = self.producer
        product.save()
        
        self.assertEqual(product.price, Decimal('3.50'))
        self.assertGreater(product.price, 0)
    
    def test_seasonal_status_displayed(self):
        form = ProductForm(data=self.product_data)
        self.assertTrue(form.is_valid())
        product = form.save(commit=False)
        product.producer = self.producer
        product.save()
        
        self.assertEqual(
            product.seasonal_status,
            Product.SeasonalStatus.IN_SEASON,
            "Seasonal status should be set to In Season"
        )
        
        self.assertEqual(
            product.get_seasonal_status_display(),
            "In Season",
            "Seasonal status display should show 'In Season'"
        )
    
    def test_stock_quantity_tracked(self):
        form = ProductForm(data=self.product_data)
        self.assertTrue(form.is_valid())
        product = form.save(commit=False)
        product.producer = self.producer
        product.save()
        
        self.assertEqual(product.stock_quantity, 50)
        
        product.stock_quantity = 45
        product.save()
        
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 45)
    
    def test_allergen_information_stored(self):
        form = ProductForm(data=self.product_data)
        self.assertTrue(form.is_valid())
        product = form.save(commit=False)
        product.producer = self.producer
        product.save()
        
        self.assertEqual(product.allergen_info, 'Contains eggs')
    
    def test_harvest_date_stored(self):
        form = ProductForm(data=self.product_data)
        self.assertTrue(form.is_valid())
        product = form.save(commit=False)
        product.producer = self.producer
        product.save()
        
        self.assertEqual(product.harvest_date, timezone.now().date())
    
    def test_invalid_price_rejected(self):
        invalid_data = self.product_data.copy()
        invalid_data['price'] = Decimal('0')
        
        form = ProductForm(data=invalid_data)
        self.assertFalse(
            form.is_valid(),
            "Form should be invalid with price of 0"
        )
        self.assertIn(
            'price',
            form.errors,
            "Form should have an error for the price field"
        )
    
    def test_negative_stock_rejected(self):
        invalid_data = self.product_data.copy()
        invalid_data['stock_quantity'] = -5
        
        form = ProductForm(data=invalid_data)
        self.assertFalse(
            form.is_valid(),
            "Form should be invalid with negative stock quantity"
        )
        self.assertIn(
            'stock_quantity',
            form.errors,
            "Form should have an error for the stock_quantity field"
        )
    
    def test_product_requires_producer_authentication(self):
        response = self.client.post(self.add_product_url, data=self.product_data)
        
        self.assertNotEqual(response.status_code, 200)
    
    def test_product_unit_options(self):
        form = ProductForm(data=self.product_data)
        self.assertTrue(form.is_valid())
        product = form.save(commit=False)
        product.producer = self.producer
        product.save()
        
        self.assertEqual(product.unit, Product.Unit.DOZEN)
        self.assertEqual(product.get_unit_display(), "Dozen")
    
    def test_product_availability_toggle(self):
        form = ProductForm(data=self.product_data)
        self.assertTrue(form.is_valid())
        product = form.save(commit=False)
        product.producer = self.producer
        product.save()
        
        self.assertTrue(product.is_available)
        
        product.is_available = False
        product.save()
        
        product.refresh_from_db()
        self.assertFalse(product.is_available)
    
    def test_required_fields_validation(self):
        invalid_data = self.product_data.copy()
        invalid_data['name'] = ''
        
        form = ProductForm(data=invalid_data)
        self.assertFalse(
            form.is_valid(),
            "Form should be invalid when name is missing"
        )
        
        invalid_data = self.product_data.copy()
        invalid_data['price'] = None
        
        form = ProductForm(data=invalid_data)
        self.assertFalse(
            form.is_valid(),
            "Form should be invalid when price is missing"
        )
        
        invalid_data = self.product_data.copy()
        invalid_data['category'] = None
        
        form = ProductForm(data=invalid_data)
        self.assertFalse(
            form.is_valid(),
            "Form should be invalid when category is missing"
        )
