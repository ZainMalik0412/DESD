from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import FieldDoesNotExist

from accounts.models import CustomUser
from marketplace.models import Product, Category
from marketplace.forms import ProductForm


class TC014OrganicCertificationFilterTests(TestCase):
    """
    Test Case ID: TC-014
    User Story: As a customer, I want to filter products by organic certification
    so that I can find certified organic items.
    """

    def setUp(self):
        self.client = Client()
        self.browse_url = reverse('browse')

        self.customer = CustomUser.objects.create_user(
            username='customer_tc014',
            email='customer_tc014@test.com',
            password='Password123!',
            role=CustomUser.Role.CUSTOMER,
            first_name='Chris',
            last_name='Buyer'
        )

        self.producer = CustomUser.objects.create_user(
            username='producer_tc014',
            email='producer_tc014@test.com',
            password='Password123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Jane',
            last_name='Farmer'
        )

        self.vegetables = Category.objects.create(
            name='Vegetables',
            slug='vegetables',
            description='Fresh vegetables',
            is_active=True
        )

        self.fruits = Category.objects.create(
            name='Fruits',
            slug='fruits',
            description='Fresh fruits',
            is_active=True
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

        self.certified_products = [
            self._create_product('Tomatoes', self.vegetables, certified=True),
            self._create_product('Carrots', self.vegetables, certified=True),
            self._create_product('Apples', self.fruits, certified=True),
            self._create_product('Milk', self.dairy, certified=True),
            self._create_product('Yogurt', self.dairy, certified=True),
        ]

        self.non_certified_products = [
            self._create_product('Potatoes', self.vegetables, certified=False),
            self._create_product('Onions', self.vegetables, certified=False),
            self._create_product('Bananas', self.fruits, certified=False),
            self._create_product('Bread', self.bakery, certified=False),
            self._create_product('Croissant', self.bakery, certified=False),
        ]

        self.certified_names = [p.name for p in self.certified_products]
        self.non_certified_names = [p.name for p in self.non_certified_products]

        self.sample_certified_product = self.certified_products[0]
        self.sample_certified_product_detail_url = reverse(
            'product_detail',
            args=[self.sample_certified_product.id]
        )

    def _organic_field_exists(self):
        try:
            Product._meta.get_field('organic_certification_status')
            return True
        except FieldDoesNotExist:
            return False

    def _create_product(self, name, category, certified):
        kwargs = {
            'producer': self.producer,
            'category': category,
            'name': name,
            'description': f'{name} description',
            'price': Decimal('3.50'),
            'unit': Product.Unit.KG,
            'stock_quantity': 20,
            'is_available': True,
            'seasonal_status': Product.SeasonalStatus.IN_SEASON,
        }

        if self._organic_field_exists():
            kwargs['organic_certification_status'] = (
                'certified_organic' if certified else 'not_certified'
            )

        return Product.objects.create(**kwargs)

    def _login_customer(self):
        self.client.login(username='customer_tc014', password='Password123!')

    def test_product_model_has_organic_certification_field(self):
        """
        Acceptance criteria:
        organic certification status is accurately maintained for each product.
        """
        field = Product._meta.get_field('organic_certification_status')
        self.assertIsNotNone(field)

    def test_product_form_exposes_organic_certification_field_for_producers(self):
        """
        Acceptance criteria:
        producers can set certification status when listing products.
        """
        form = ProductForm()
        self.assertIn('organic_certification_status', form.fields)

    def test_browse_page_shows_organic_certification_filter_control(self):
        """
        Steps 1-3:
        navigate to browse page, locate filtering options,
        and see the organic certification filter.
        """
        self._login_customer()
        response = self.client.get(self.browse_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Organic Certification')
        self.assertContains(response, 'Certified Organic')

    def test_certified_organic_filter_returns_only_certified_products(self):
        """
        Steps 4-6 + expected results:
        enabling certified organic filter should only show certified products.
        """
        self._login_customer()
        response = self.client.get(self.browse_url, {
            'organic_certification': 'certified_organic'
        })

        self.assertEqual(response.status_code, 200)

        products = response.context['products']
        product_names = [p.name for p in products]

        for name in self.certified_names:
            self.assertIn(name, product_names)

        for name in self.non_certified_names:
            self.assertNotIn(name, product_names)

    def test_filtered_products_display_certification_indicator_on_browse_page(self):
        """
        Expected results:
        all filtered products display organic certification badge/indicator.
        """
        self._login_customer()
        response = self.client.get(self.browse_url, {
            'organic_certification': 'certified_organic'
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Certified Organic')
        self.assertNotContains(response, 'Not Certified')

    def test_product_detail_shows_organic_certification_information(self):
        """
        Steps 7-8:
        click a filtered product and verify product detail shows certification info.
        """
        self._login_customer()
        response = self.client.get(self.sample_certified_product_detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Certified Organic')

    def test_clearing_filter_returns_all_products(self):
        """
        Step 9:
        clearing the filter should return all products again.
        """
        self._login_customer()

        filtered_response = self.client.get(self.browse_url, {
            'organic_certification': 'certified_organic'
        })
        self.assertEqual(filtered_response.status_code, 200)

        filtered_products = filtered_response.context['products']
        filtered_count = len(filtered_products)

        unfiltered_response = self.client.get(self.browse_url)
        self.assertEqual(unfiltered_response.status_code, 200)

        all_products = unfiltered_response.context['products']
        all_count = len(all_products)

        self.assertLess(filtered_count, all_count)
        self.assertGreaterEqual(all_count, 10)

    def test_empty_results_message_when_no_certified_products_exist_in_category(self):
        """
        Step 10 + expected results:
        applying the organic filter in a category with no certified products
        should show empty results and an appropriate message.
        """
        self._login_customer()
        response = self.client.get(self.browse_url, {
            'category': 'bakery',
            'organic_certification': 'certified_organic'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['products']), 0)
        self.assertContains(response, 'No products found')

    def test_organic_filter_combines_with_category_filter(self):
        """
        Acceptance criteria:
        filter works consistently across categories and combines logically with other filters.
        """
        self._login_customer()
        response = self.client.get(self.browse_url, {
            'category': 'vegetables',
            'organic_certification': 'certified_organic'
        })

        self.assertEqual(response.status_code, 200)

        products = response.context['products']
        product_names = [p.name for p in products]

        self.assertIn('Tomatoes', product_names)
        self.assertIn('Carrots', product_names)
        self.assertNotIn('Potatoes', product_names)
        self.assertNotIn('Onions', product_names)

        for product in products:
            self.assertEqual(product.category.slug, 'vegetables')