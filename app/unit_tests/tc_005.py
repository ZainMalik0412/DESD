from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from accounts.models import CustomUser
from marketplace.models import Product, Category


class TC005ProductSearchTest(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.browse_url = reverse('browse')
        
        self.producer1 = CustomUser.objects.create_user(
            username='organicfarm',
            email='producer@organicfarm.com',
            password='ProducerPass123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Sarah',
            last_name='Green'
        )
        
        self.producer2 = CustomUser.objects.create_user(
            username='localfarm',
            email='producer@localfarm.com',
            password='ProducerPass123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Michael',
            last_name='Brown'
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
        
        self.fruits_category = Category.objects.create(
            name='Fruits',
            slug='fruits',
            description='Fresh local fruits',
            is_active=True
        )
        
        Product.objects.create(
            producer=self.producer1,
            category=self.vegetables_category,
            name='Organic Tomatoes',
            description='Fresh organic tomatoes grown locally',
            price=Decimal('3.50'),
            unit=Product.Unit.KG,
            stock_quantity=30,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
        )
        
        Product.objects.create(
            producer=self.producer1,
            category=self.vegetables_category,
            name='Cherry Tomatoes',
            description='Sweet cherry tomatoes perfect for salads',
            price=Decimal('4.00'),
            unit=Product.Unit.PACK,
            stock_quantity=20,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
        )
        
        Product.objects.create(
            producer=self.producer2,
            category=self.vegetables_category,
            name='Organic Carrots',
            description='Fresh organic carrots from local farm',
            price=Decimal('2.50'),
            unit=Product.Unit.KG,
            stock_quantity=40,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.ALL_YEAR,
        )
        
        Product.objects.create(
            producer=self.producer1,
            category=self.dairy_category,
            name='Organic Milk',
            description='Fresh organic milk from grass-fed cows',
            price=Decimal('3.00'),
            unit=Product.Unit.L,
            stock_quantity=25,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.ALL_YEAR,
        )
        
        Product.objects.create(
            producer=self.producer2,
            category=self.fruits_category,
            name='Organic Apples',
            description='Crisp organic apples straight from the orchard',
            price=Decimal('3.50'),
            unit=Product.Unit.KG,
            stock_quantity=35,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
        )
        
        Product.objects.create(
            producer=self.producer1,
            category=self.vegetables_category,
            name='Fresh Lettuce',
            description='Green lettuce freshly harvested',
            price=Decimal('2.00'),
            unit=Product.Unit.ITEM,
            stock_quantity=15,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
        )
    
    def test_search_bar_accessible(self):
        response = self.client.get(self.browse_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'search')
    
    def test_search_for_tomatoes(self):
        response = self.client.get(self.browse_url, {'search': 'tomatoes'})
        
        self.assertEqual(response.status_code, 200)
        
        products = response.context['products']
        product_names = [p.name for p in products]
        
        self.assertIn('Organic Tomatoes', product_names)
        self.assertIn('Cherry Tomatoes', product_names)
        self.assertEqual(len(products), 2)
    
    def test_search_for_organic(self):
        response = self.client.get(self.browse_url, {'search': 'organic'})
        
        self.assertEqual(response.status_code, 200)
        
        products = response.context['products']
        product_names = [p.name for p in products]
        
        self.assertIn('Organic Tomatoes', product_names)
        self.assertIn('Organic Carrots', product_names)
        self.assertIn('Organic Milk', product_names)
        self.assertIn('Organic Apples', product_names)
        
        self.assertGreaterEqual(len(products), 4)
    
    def test_search_results_from_different_categories(self):
        response = self.client.get(self.browse_url, {'search': 'organic'})
        
        products = response.context['products']
        
        categories = set(p.category.name for p in products)
        
        self.assertIn('Vegetables', categories)
        self.assertIn('Dairy Products', categories)
        self.assertIn('Fruits', categories)
        self.assertGreaterEqual(len(categories), 3)
    
    def test_search_nonexistent_product(self):
        response = self.client.get(self.browse_url, {'search': 'nonexistentproduct'})
        
        self.assertEqual(response.status_code, 200)
        
        products = response.context['products']
        self.assertEqual(len(products), 0)
    
    def test_search_case_insensitive(self):
        response_lower = self.client.get(self.browse_url, {'search': 'tomatoes'})
        response_upper = self.client.get(self.browse_url, {'search': 'TOMATOES'})
        response_mixed = self.client.get(self.browse_url, {'search': 'ToMaToEs'})
        
        products_lower = list(response_lower.context['products'])
        products_upper = list(response_upper.context['products'])
        products_mixed = list(response_mixed.context['products'])
        
        self.assertEqual(len(products_lower), len(products_upper))
        self.assertEqual(len(products_lower), len(products_mixed))
        self.assertEqual(len(products_lower), 2)
    
    def test_search_by_product_name(self):
        response = self.client.get(self.browse_url, {'search': 'Carrots'})
        
        products = response.context['products']
        product_names = [p.name for p in products]
        
        self.assertIn('Organic Carrots', product_names)
        self.assertEqual(len(products), 1)
    
    def test_search_by_partial_name(self):
        response = self.client.get(self.browse_url, {'search': 'tomat'})
        
        products = response.context['products']
        product_names = [p.name for p in products]
        
        self.assertIn('Organic Tomatoes', product_names)
        self.assertIn('Cherry Tomatoes', product_names)
        self.assertGreaterEqual(len(products), 2)
    
    def test_search_results_display_product_info(self):
        response = self.client.get(self.browse_url, {'search': 'tomatoes'})
        
        products = response.context['products']
        
        for product in products:
            self.assertIsNotNone(product.name)
            self.assertIsNotNone(product.price)
            self.assertIsNotNone(product.producer)
            self.assertIsNotNone(product.category)
            
            self.assertGreater(len(product.name), 0)
            self.assertGreater(product.price, 0)
    
    def test_search_results_show_producer(self):
        response = self.client.get(self.browse_url, {'search': 'organic'})
        
        products = response.context['products']
        
        for product in products:
            self.assertIsNotNone(product.producer.username)
            self.assertIn(
                product.producer.username,
                ['organicfarm', 'localfarm']
            )
    
    def test_search_results_show_category(self):
        response = self.client.get(self.browse_url, {'search': 'organic'})
        
        products = response.context['products']
        
        for product in products:
            self.assertIsNotNone(product.category.name)
            self.assertGreater(len(product.category.name), 0)
    
    def test_empty_search_shows_all_products(self):
        response = self.client.get(self.browse_url, {'search': ''})
        
        products = response.context['products']
        
        self.assertGreaterEqual(len(products), 6)
    
    def test_search_term_in_context(self):
        response = self.client.get(self.browse_url, {'search': 'tomatoes'})
        
        self.assertEqual(response.context['search'], 'tomatoes')
    
    def test_search_with_whitespace(self):
        response = self.client.get(self.browse_url, {'search': '  tomatoes  '})
        
        products = response.context['products']
        product_names = [p.name for p in products]
        
        self.assertIn('Organic Tomatoes', product_names)
        self.assertIn('Cherry Tomatoes', product_names)
    
    def test_search_single_character(self):
        response = self.client.get(self.browse_url, {'search': 'o'})
        
        products = response.context['products']
        
        self.assertGreater(len(products), 0)
    
    def test_search_multiple_word_product(self):
        response = self.client.get(self.browse_url, {'search': 'Cherry Tomatoes'})
        
        products = response.context['products']
        product_names = [p.name for p in products]
        
        self.assertIn('Cherry Tomatoes', product_names)
    
    def test_search_returns_only_available_products(self):
        Product.objects.create(
            producer=self.producer1,
            category=self.vegetables_category,
            name='Unavailable Tomatoes',
            description='These should not appear in search',
            price=Decimal('5.00'),
            unit=Product.Unit.KG,
            stock_quantity=0,
            is_available=False,
            seasonal_status=Product.SeasonalStatus.OUT_OF_SEASON,
        )
        
        response = self.client.get(self.browse_url, {'search': 'tomatoes'})
        
        products = response.context['products']
        product_names = [p.name for p in products]
        
        self.assertNotIn('Unavailable Tomatoes', product_names)
        self.assertEqual(len(products), 2)
    
    def test_search_with_special_characters(self):
        response = self.client.get(self.browse_url, {'search': 'organic@'})
        
        self.assertEqual(response.status_code, 200)
        
        products = response.context['products']
        self.assertEqual(len(products), 0)
    
    def test_search_performance_acceptable(self):
        import time
        
        start_time = time.time()
        response = self.client.get(self.browse_url, {'search': 'organic'})
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        
        execution_time = end_time - start_time
        self.assertLess(execution_time, 2.0)
    
    def test_search_milk(self):
        response = self.client.get(self.browse_url, {'search': 'milk'})
        
        products = response.context['products']
        product_names = [p.name for p in products]
        
        self.assertIn('Organic Milk', product_names)
        self.assertEqual(len(products), 1)
    
    def test_search_lettuce(self):
        response = self.client.get(self.browse_url, {'search': 'lettuce'})
        
        products = response.context['products']
        product_names = [p.name for p in products]
        
        self.assertIn('Fresh Lettuce', product_names)
        self.assertEqual(len(products), 1)
    
    def test_search_fresh(self):
        response = self.client.get(self.browse_url, {'search': 'fresh'})
        
        products = response.context['products']
        
        self.assertGreater(len(products), 0)
        
        for product in products:
            self.assertTrue(
                'fresh' in product.name.lower() or 'fresh' in product.description.lower()
            )
    
    def test_no_search_parameter_shows_all(self):
        response = self.client.get(self.browse_url)
        
        products = response.context['products']
        
        self.assertGreaterEqual(len(products), 6)
    
    def test_search_result_shows_price(self):
        response = self.client.get(self.browse_url, {'search': 'tomatoes'})
        
        products = response.context['products']
        
        for product in products:
            self.assertIsInstance(product.price, Decimal)
            self.assertGreater(product.price, Decimal('0'))
    
    def test_search_combined_with_category_filter(self):
        response = self.client.get(self.browse_url, {
            'search': 'organic',
            'category': 'vegetables'
        })
        
        products = response.context['products']
        product_names = [p.name for p in products]
        
        self.assertIn('Organic Tomatoes', product_names)
        self.assertIn('Organic Carrots', product_names)
        
        self.assertNotIn('Organic Milk', product_names)
        self.assertNotIn('Organic Apples', product_names)
        
        for product in products:
            self.assertEqual(product.category.slug, 'vegetables')
