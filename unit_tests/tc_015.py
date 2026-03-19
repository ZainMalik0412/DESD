from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import CustomUser
from marketplace.models import Product, Category
from marketplace.forms import ProductForm


class TC015AllergenWarningTests(TestCase):
    """
    Test Case ID: TC-015
    User Story: As a customer, I want to see allergen warnings clearly displayed
    so that I can avoid products that may harm me or my family.
    """

    def setUp(self):
        self.client = Client()

        self.customer = CustomUser.objects.create_user(
            username='customer_tc015',
            email='customer_tc015@test.com',
            password='Password123!',
            role=CustomUser.Role.CUSTOMER,
            first_name='Chris',
            last_name='Buyer'
        )

        self.producer = CustomUser.objects.create_user(
            username='producer_tc015',
            email='producer_tc015@test.com',
            password='Password123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Jane',
            last_name='Farmer'
        )

        self.dairy = Category.objects.create(
            name='Dairy Products',
            slug='dairy-products',
            description='Fresh dairy products',
            is_active=True
        )

        self.bakery = Category.objects.create(
            name='Bakery',
            slug='bakery',
            description='Fresh bakery products',
            is_active=True
        )

        self.fruits = Category.objects.create(
            name='Fruits',
            slug='fruits',
            description='Fresh fruits',
            is_active=True
        )

        self.pasta = Category.objects.create(
            name='Pasta',
            slug='pasta',
            description='Fresh pasta',
            is_active=True
        )

        # Product containing dairy
        self.cheddar_cheese = Product.objects.create(
            producer=self.producer,
            category=self.dairy,
            name='Cheddar Cheese',
            description='Mature cheddar',
            price=Decimal('4.50'),
            unit=Product.Unit.ITEM,
            stock_quantity=10,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
            allergen_info='Contains: Milk'
        )

        # Product containing multiple allergens
        self.walnut_bread = Product.objects.create(
            producer=self.producer,
            category=self.bakery,
            name='Walnut Bread',
            description='Fresh walnut bread loaf',
            price=Decimal('3.20'),
            unit=Product.Unit.ITEM,
            stock_quantity=12,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
            allergen_info='Contains: Wheat (Gluten), Nuts (Walnuts)'
        )

        # Third product with allergens to satisfy preconditions
        self.egg_pasta = Product.objects.create(
            producer=self.producer,
            category=self.pasta,
            name='Fresh Egg Pasta',
            description='Handmade pasta',
            price=Decimal('2.80'),
            unit=Product.Unit.PACK,
            stock_quantity=8,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
            allergen_info='Contains: Eggs, Wheat (Gluten)'
        )

        # Product with no allergens
        self.fresh_apples = Product.objects.create(
            producer=self.producer,
            category=self.fruits,
            name='Fresh Apples',
            description='Crisp apples',
            price=Decimal('2.50'),
            unit=Product.Unit.KG,
            stock_quantity=15,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
            allergen_info=''
        )

        self.browse_url = reverse('browse')
        self.cheddar_url = reverse('product_detail', args=[self.cheddar_cheese.id])
        self.walnut_bread_url = reverse('product_detail', args=[self.walnut_bread.id])
        self.apples_url = reverse('product_detail', args=[self.fresh_apples.id])

    def _login_customer(self):
        self.client.login(username='customer_tc015', password='Password123!')

    def _valid_product_form_data(self, **overrides):
        data = {
            'name': 'Test Food Product',
            'description': 'Test description',
            'price': '3.99',
            'unit': Product.Unit.ITEM,
            'stock_quantity': 10,
            'category': self.dairy.id,
            'is_available': 'on',
            'seasonal_status': Product.SeasonalStatus.IN_SEASON,
            'allergen_info': 'Contains: Milk',
            'harvest_date': '',
        }
        data.update(overrides)
        return data

    def test_product_detail_shows_single_allergen_warning_for_dairy_product(self):
        """
        Steps 1-4:
        browse to dairy product and verify 'Contains: Milk' is clearly displayed.
        """
        self._login_customer()
        response = self.client.get(self.cheddar_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Contains: Milk')

    def test_product_detail_shows_multiple_allergens_individually(self):
        """
        Steps 5-6:
        verify multiple allergens are shown for Walnut Bread.
        """
        self._login_customer()
        response = self.client.get(self.walnut_bread_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Contains: Wheat (Gluten), Nuts (Walnuts)')
        self.assertContains(response, 'Wheat (Gluten)')
        self.assertContains(response, 'Nuts (Walnuts)')

    def test_product_with_no_allergens_shows_clear_no_allergens_message(self):
        """
        Steps 7-8:
        products with no allergens should clearly state that.
        """
        self._login_customer()
        response = self.client.get(self.apples_url)

        self.assertEqual(response.status_code, 200)
        page = response.content.decode()

        self.assertTrue(
            'No common allergens' in page or 'No allergens' in page,
            "Products without allergens should clearly state this"
        )

    def test_allergen_information_is_visible_before_add_to_cart(self):
        """
        Expected results:
        allergen information should be visible before ordering.
        """
        self._login_customer()
        response = self.client.get(self.cheddar_url)

        self.assertEqual(response.status_code, 200)
        page = response.content.decode()

        allergen_pos = page.find('Contains: Milk')
        add_to_cart_pos = page.find('Add to Cart')

        self.assertNotEqual(allergen_pos, -1)
        self.assertNotEqual(add_to_cart_pos, -1)
        self.assertLess(allergen_pos, add_to_cart_pos)

    def test_search_for_nuts_finds_products_by_allergen_information(self):
        """
        Steps 9-10:
        search for products containing nuts and verify allergen-based searching works.
        """
        self._login_customer()
        response = self.client.get(self.browse_url, {'search': 'nuts'})

        self.assertEqual(response.status_code, 200)
        products = response.context['products']
        product_names = [p.name for p in products]

        self.assertIn('Walnut Bread', product_names)

    def test_browse_page_supports_allergen_filtering(self):
        """
        Acceptance criteria:
        customers can filter by allergen presence/absence.
        """
        self._login_customer()
        response = self.client.get(self.browse_url)

        self.assertEqual(response.status_code, 200)
        page = response.content.decode()

        self.assertTrue(
            'Allergen' in page or 'allergen' in page,
            "Browse page should include allergen filtering controls"
        )

    def test_product_form_requires_allergen_information_for_food_products(self):
        """
        Acceptance criteria:
        producers must provide allergen information and it cannot be omitted.
        """
        form = ProductForm(data=self._valid_product_form_data(allergen_info=''))

        self.assertFalse(form.is_valid())
        self.assertIn('allergen_info', form.errors)

    def test_product_form_accepts_full_uk_major_allergens_text(self):
        """
        Expected results:
        all 14 major UK allergens can be specified.
        """
        all_14_allergens = (
            'Contains: Celery, Cereals containing Gluten, Crustaceans, Eggs, Fish, '
            'Lupin, Milk, Molluscs, Mustard, Peanuts, Sesame, Soybeans, '
            'Sulphur Dioxide/Sulphites, Tree Nuts'
        )

        form = ProductForm(data=self._valid_product_form_data(
            name='Full Allergen Test Product',
            allergen_info=all_14_allergens
        ))

        self.assertTrue(
            form.is_valid(),
            f"Form should accept all 14 allergen labels. Errors: {form.errors}"
        )

    def test_allergen_filter_can_return_only_products_with_allergens(self):
        """
        Acceptance criteria:
        customers can filter by allergen presence.
        """
        self._login_customer()
        response = self.client.get(self.browse_url, {'allergen_filter': 'has_allergens'})

        self.assertEqual(response.status_code, 200)
        products = response.context['products']
        product_names = [p.name for p in products]

        self.assertIn('Cheddar Cheese', product_names)
        self.assertIn('Walnut Bread', product_names)
        self.assertIn('Fresh Egg Pasta', product_names)
        self.assertNotIn('Fresh Apples', product_names)