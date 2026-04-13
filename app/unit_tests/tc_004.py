from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from accounts.models import CustomUser
from marketplace.models import Product, Category


class TC004CategoryBrowsingTest(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.browse_url = reverse('browse')
        
        self.producer1 = CustomUser.objects.create_user(
            username='greenvalleyfarm',
            email='producer1@greenvalley.com',
            password='ProducerPass123!',
            role=CustomUser.Role.PRODUCER,
            first_name='John',
            last_name='Green'
        )
        
        self.producer2 = CustomUser.objects.create_user(
            username='bristolvalleyfarm',
            email='producer2@bristolvalley.com',
            password='ProducerPass123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Jane',
            last_name='Smith'
        )
        
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
        
        self.bakery_category = Category.objects.create(
            name='Bakery',
            slug='bakery',
            description='Fresh baked goods',
            is_active=True
        )
        
        self.vegetable_products = []
        vegetable_names = ['Organic Carrots', 'Fresh Lettuce', 'Tomatoes', 'Cucumbers', 'Bell Peppers']
        for i, name in enumerate(vegetable_names):
            product = Product.objects.create(
                producer=self.producer1,
                category=self.vegetables_category,
                name=name,
                description=f'Fresh organic {name.lower()}',
                price=Decimal('2.50') + Decimal(i * 0.5),
                unit=Product.Unit.KG,
                stock_quantity=20 + i * 5,
                is_available=True,
                seasonal_status=Product.SeasonalStatus.IN_SEASON,
            )
            self.vegetable_products.append(product)
        
        self.dairy_products = []
        dairy_names = ['Organic Milk', 'Fresh Butter', 'Cheddar Cheese']
        for i, name in enumerate(dairy_names):
            product = Product.objects.create(
                producer=self.producer2,
                category=self.dairy_category,
                name=name,
                description=f'Fresh {name.lower()}',
                price=Decimal('3.00') + Decimal(i * 1.0),
                unit=Product.Unit.L if 'Milk' in name else Product.Unit.KG,
                stock_quantity=15 + i * 5,
                is_available=True,
                seasonal_status=Product.SeasonalStatus.ALL_YEAR,
            )
            self.dairy_products.append(product)
        
        self.bakery_product = Product.objects.create(
            producer=self.producer1,
            category=self.bakery_category,
            name='Sourdough Bread',
            description='Fresh baked sourdough bread',
            price=Decimal('4.50'),
            unit=Product.Unit.ITEM,
            stock_quantity=10,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.ALL_YEAR,
        )
    
    def test_browse_page_loads(self):
        response = self.client.get(self.browse_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/browse.html')
    
    def test_category_navigation_visible(self):
        response = self.client.get(self.browse_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('categories', response.context)
        
        categories = response.context['categories']
        self.assertGreaterEqual(len(categories), 3)
        
        category_names = [cat.name for cat in categories]
        self.assertIn('Vegetables', category_names)
        self.assertIn('Dairy Products', category_names)
        self.assertIn('Bakery', category_names)
    
    def test_vegetables_category_filtering(self):
        response = self.client.get(self.browse_url, {'category': 'vegetables'})
        
        self.assertEqual(response.status_code, 200)
        
        products = response.context['products']
        self.assertEqual(len(products), 5, "Should display 5 vegetable products")
        
        for product in products:
            self.assertEqual(
                product.category.slug,
                'vegetables',
                f"Product {product.name} should be in Vegetables category"
            )
    
    def test_dairy_category_filtering(self):
        response = self.client.get(self.browse_url, {'category': 'dairy-products'})
        
        self.assertEqual(response.status_code, 200)
        
        products = response.context['products']
        self.assertEqual(len(products), 3, "Should display 3 dairy products")
        
        for product in products:
            self.assertEqual(
                product.category.slug,
                'dairy-products',
                f"Product {product.name} should be in Dairy Products category"
            )
    
    def test_vegetables_display_only_vegetables(self):
        response = self.client.get(self.browse_url, {'category': 'vegetables'})
        
        products = response.context['products']
        product_names = [p.name for p in products]
        
        self.assertIn('Organic Carrots', product_names)
        self.assertIn('Fresh Lettuce', product_names)
        self.assertIn('Tomatoes', product_names)
        self.assertIn('Cucumbers', product_names)
        self.assertIn('Bell Peppers', product_names)
        
        self.assertNotIn('Organic Milk', product_names)
        self.assertNotIn('Sourdough Bread', product_names)
    
    def test_dairy_display_only_dairy(self):
        response = self.client.get(self.browse_url, {'category': 'dairy-products'})
        
        products = response.context['products']
        product_names = [p.name for p in products]
        
        self.assertIn('Organic Milk', product_names)
        self.assertIn('Fresh Butter', product_names)
        self.assertIn('Cheddar Cheese', product_names)
        
        self.assertNotIn('Organic Carrots', product_names)
        self.assertNotIn('Sourdough Bread', product_names)
    
    def test_products_correctly_categorised(self):
        vegetable_response = self.client.get(self.browse_url, {'category': 'vegetables'})
        vegetable_products = vegetable_response.context['products']
        
        for product in vegetable_products:
            self.assertEqual(product.category.name, 'Vegetables')
        
        dairy_response = self.client.get(self.browse_url, {'category': 'dairy-products'})
        dairy_products = dairy_response.context['products']
        
        for product in dairy_products:
            self.assertEqual(product.category.name, 'Dairy Products')
    
    def test_product_information_display(self):
        response = self.client.get(self.browse_url, {'category': 'vegetables'})
        
        products = response.context['products']
        
        for product in products:
            self.assertIsNotNone(product.name, "Product should have a name")
            self.assertIsNotNone(product.price, "Product should have a price")
            self.assertIsNotNone(product.producer, "Product should have a producer")
            self.assertIsNotNone(product.is_available, "Product should have availability status")
            
            self.assertGreater(len(product.name), 0)
            self.assertGreater(product.price, 0)
    
    def test_producer_name_displayed(self):
        response = self.client.get(self.browse_url, {'category': 'vegetables'})
        
        products = response.context['products']
        
        for product in products:
            self.assertEqual(product.producer.username, 'greenvalleyfarm')
            self.assertIsNotNone(product.producer.first_name)
            self.assertIsNotNone(product.producer.last_name)
    
    def test_only_available_products_displayed(self):
        unavailable_product = Product.objects.create(
            producer=self.producer1,
            category=self.vegetables_category,
            name='Unavailable Product',
            description='This should not appear',
            price=Decimal('5.00'),
            unit=Product.Unit.KG,
            stock_quantity=0,
            is_available=False,
            seasonal_status=Product.SeasonalStatus.OUT_OF_SEASON,
        )
        
        response = self.client.get(self.browse_url, {'category': 'vegetables'})
        
        products = response.context['products']
        product_names = [p.name for p in products]
        
        self.assertNotIn('Unavailable Product', product_names)
        self.assertEqual(len(products), 5)
    
    def test_all_categories_show_all_products(self):
        response = self.client.get(self.browse_url)
        
        products = response.context['products']
        
        self.assertGreaterEqual(len(products), 9)
        
        product_names = [p.name for p in products]
        self.assertIn('Organic Carrots', product_names)
        self.assertIn('Organic Milk', product_names)
        self.assertIn('Sourdough Bread', product_names)
    
    def test_category_page_loads_without_errors(self):
        categories_to_test = ['vegetables', 'dairy-products', 'bakery']
        
        for category_slug in categories_to_test:
            response = self.client.get(self.browse_url, {'category': category_slug})
            self.assertEqual(
                response.status_code,
                200,
                f"Category page {category_slug} should load without errors"
            )
    
    def test_navigation_between_categories(self):
        response1 = self.client.get(self.browse_url, {'category': 'vegetables'})
        self.assertEqual(response1.status_code, 200)
        products1 = response1.context['products']
        self.assertEqual(len(products1), 5)
        
        response2 = self.client.get(self.browse_url, {'category': 'dairy-products'})
        self.assertEqual(response2.status_code, 200)
        products2 = response2.context['products']
        self.assertEqual(len(products2), 3)
        
        response3 = self.client.get(self.browse_url)
        self.assertEqual(response3.status_code, 200)
        products3 = response3.context['products']
        self.assertGreaterEqual(len(products3), 9)
    
    def test_product_price_displayed(self):
        response = self.client.get(self.browse_url, {'category': 'vegetables'})
        
        products = response.context['products']
        
        for product in products:
            self.assertIsInstance(product.price, Decimal)
            self.assertGreater(product.price, Decimal('0'))
    
    def test_product_availability_status_shown(self):
        response = self.client.get(self.browse_url, {'category': 'vegetables'})
        
        products = response.context['products']
        
        for product in products:
            self.assertTrue(product.is_available)
    
    def test_seasonal_status_filtering(self):
        response = self.client.get(self.browse_url, {'category': 'vegetables'})
        
        products = response.context['products']
        
        for product in products:
            self.assertIn(
                product.seasonal_status,
                [Product.SeasonalStatus.IN_SEASON, Product.SeasonalStatus.ALL_YEAR]
            )
    
    def test_category_has_minimum_products(self):
        vegetable_response = self.client.get(self.browse_url, {'category': 'vegetables'})
        vegetable_products = vegetable_response.context['products']
        self.assertGreaterEqual(
            len(vegetable_products),
            5,
            "Vegetables category should have at least 5 products"
        )
        
        dairy_response = self.client.get(self.browse_url, {'category': 'dairy-products'})
        dairy_products = dairy_response.context['products']
        self.assertGreaterEqual(
            len(dairy_products),
            3,
            "Dairy category should have at least 3 products"
        )
    
    def test_selected_category_in_context(self):
        response = self.client.get(self.browse_url, {'category': 'vegetables'})
        
        self.assertEqual(response.context['selected_category'], 'vegetables')
    
    def test_inactive_category_not_shown(self):
        inactive_category = Category.objects.create(
            name='Inactive Category',
            slug='inactive',
            description='This should not appear',
            is_active=False
        )
        
        response = self.client.get(self.browse_url)
        
        categories = response.context['categories']
        category_names = [cat.name for cat in categories]
        
        self.assertNotIn('Inactive Category', category_names)
    
    def test_product_complete_information(self):
        response = self.client.get(self.browse_url, {'category': 'vegetables'})
        
        products = response.context['products']
        
        for product in products:
            self.assertTrue(len(product.name) > 0, "Product name should not be empty")
            self.assertTrue(len(product.description) > 0, "Product description should not be empty")
            self.assertGreater(product.price, 0, "Product price should be positive")
            self.assertGreaterEqual(product.stock_quantity, 0, "Stock quantity should be non-negative")
            self.assertIsNotNone(product.unit, "Product unit should be set")
            self.assertIsNotNone(product.producer.username, "Producer username should be set")
    
    def test_multiple_producers_in_categories(self):
        response = self.client.get(self.browse_url)
        
        products = response.context['products']
        
        producers = set(p.producer.username for p in products)
        
        self.assertIn('greenvalleyfarm', producers)
        self.assertIn('bristolvalleyfarm', producers)
        self.assertGreaterEqual(len(producers), 2)
