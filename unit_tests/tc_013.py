from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import CustomUser, Address
from marketplace.models import Product, Category


class TC013FoodMilesTests(TestCase):
    """
    Test Case ID: TC-013
    User Story: As a customer, I want to view food miles for products
    so that I can make environmentally conscious purchases.
    """

    def setUp(self):
        self.client = Client()

        self.customer = CustomUser.objects.create_user(
            username='customer_tc013',
            email='customer_tc013@test.com',
            password='Password123!',
            role=CustomUser.Role.CUSTOMER,
            first_name='Chris',
            last_name='Buyer',
            postcode='BS1 5JG',
            delivery_address='45 Park Street, Bristol'
        )

        Address.objects.create(
            user=self.customer,
            address_line1='45 Park Street',
            address_line2='',
            city='Bristol',
            postcode='BS1 5JG',
            is_default=True
        )

        self.nearby_producer = CustomUser.objects.create_user(
            username='bristolvalleyfarm',
            email='nearby_producer@test.com',
            password='Password123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Jane',
            last_name='Smith',
            postcode='BS1 4DJ',
            delivery_address='Bristol Valley Farm'
        )

        self.far_producer = CustomUser.objects.create_user(
            username='farawayfarm',
            email='far_producer@test.com',
            password='Password123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Tom',
            last_name='Brown',
            postcode='BA1 1AA',
            delivery_address='Far Away Farm'
        )

        self.category = Category.objects.create(
            name='Vegetables',
            slug='vegetables',
            description='Fresh vegetables',
            is_active=True
        )

        self.near_product = Product.objects.create(
            producer=self.nearby_producer,
            category=self.category,
            name='Organic Tomatoes',
            description='Nearby tomatoes from Bristol Valley Farm',
            price=Decimal('3.50'),
            unit=Product.Unit.KG,
            stock_quantity=20,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
        )

        self.far_product = Product.objects.create(
            producer=self.far_producer,
            category=self.category,
            name='Farm Potatoes',
            description='Further-away potatoes from another farm',
            price=Decimal('2.80'),
            unit=Product.Unit.KG,
            stock_quantity=20,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
        )

        self.browse_url = reverse('browse')
        self.product_detail_url_near = reverse('product_detail', args=[self.near_product.id])
        self.product_detail_url_far = reverse('product_detail', args=[self.far_product.id])
        self.cart_url = reverse('orders:cart')
        self.add_near_to_cart_url = reverse('orders:add_to_cart', args=[self.near_product.id])
        self.add_far_to_cart_url = reverse('orders:add_to_cart', args=[self.far_product.id])

    def _login_customer(self):
        self.client.login(username='customer_tc013', password='Password123!')

    def test_customer_can_browse_products_in_category_before_viewing_food_miles(self):
        """
        Covers step 1 of the test case:
        customer browses products in a category before opening product detail.
        """
        self._login_customer()

        response = self.client.get(self.browse_url, {'category': 'vegetables'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Organic Tomatoes')
        self.assertContains(response, 'Farm Potatoes')

    def test_product_detail_shows_food_miles_for_logged_in_customer(self):
        """
        Covers steps 2-4:
        customer opens nearby product and sees food miles on product detail.
        """
        self._login_customer()

        response = self.client.get(self.product_detail_url_near)

        self.assertEqual(response.status_code, 200)
        self.assertIn('food_miles', response.context)
        self.assertIsNotNone(response.context['food_miles'])
        self.assertGreaterEqual(response.context['food_miles'], 0)

    def test_further_away_product_has_higher_food_miles_than_nearby_product(self):
        """
        Covers steps 5-6:
        compare a nearby product against a further-away one.
        """
        self._login_customer()

        response_near = self.client.get(self.product_detail_url_near)
        response_far = self.client.get(self.product_detail_url_far)

        self.assertEqual(response_near.status_code, 200)
        self.assertEqual(response_far.status_code, 200)

        self.assertIn('food_miles', response_near.context)
        self.assertIn('food_miles', response_far.context)

        near_miles = response_near.context['food_miles']
        far_miles = response_far.context['food_miles']

        self.assertIsNotNone(near_miles)
        self.assertIsNotNone(far_miles)
        self.assertGreater(far_miles, near_miles)

    def test_cart_shows_food_miles_for_each_added_product(self):
        """
        Covers steps 7-9:
        add both products to cart and verify cart shows food miles per item.
        """
        self._login_customer()

        self.client.post(self.add_near_to_cart_url, {'quantity': 1}, HTTP_REFERER=self.product_detail_url_near)
        self.client.post(self.add_far_to_cart_url, {'quantity': 1}, HTTP_REFERER=self.product_detail_url_far)

        response = self.client.get(self.cart_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Organic Tomatoes')
        self.assertContains(response, 'Farm Potatoes')

        self.assertIn('item_food_miles', response.context)
        self.assertIn(self.near_product.id, response.context['item_food_miles'])
        self.assertIn(self.far_product.id, response.context['item_food_miles'])

        self.assertIsNotNone(response.context['item_food_miles'][self.near_product.id])
        self.assertIsNotNone(response.context['item_food_miles'][self.far_product.id])

    def test_cart_total_food_miles_is_sum_of_individual_product_distances(self):
        """
        Covers step 10:
        total order food miles should equal sum of item food miles.
        """
        self._login_customer()

        self.client.post(self.add_near_to_cart_url, {'quantity': 1}, HTTP_REFERER=self.product_detail_url_near)
        self.client.post(self.add_far_to_cart_url, {'quantity': 1}, HTTP_REFERER=self.product_detail_url_far)

        response = self.client.get(self.cart_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('item_food_miles', response.context)
        self.assertIn('total_food_miles', response.context)

        item_food_miles = response.context['item_food_miles']
        total_food_miles = response.context['total_food_miles']

        expected_total = (
            item_food_miles[self.near_product.id] +
            item_food_miles[self.far_product.id]
        )

        self.assertEqual(total_food_miles, expected_total)

    def test_food_miles_update_if_customer_postcode_changes(self):
        """
        Covers acceptance criteria:
        food miles should update if the customer's delivery postcode changes.
        """
        self._login_customer()

        response_before = self.client.get(self.product_detail_url_near)
        self.assertEqual(response_before.status_code, 200)
        self.assertIn('food_miles', response_before.context)

        self.customer.postcode = 'EX1 1AA'
        self.customer.delivery_address = '1 Changed Address'
        self.customer.save()

        response_after = self.client.get(self.product_detail_url_near)
        self.assertEqual(response_after.status_code, 200)
        self.assertIn('food_miles', response_after.context)

        self.assertNotEqual(
            response_before.context['food_miles'],
            response_after.context['food_miles']
        )

    def test_all_products_in_browse_have_food_miles_information_available_to_customer(self):
        """
        Covers acceptance criteria:
        all products should expose food miles information to the logged-in customer.
        """
        self._login_customer()

        response = self.client.get(self.browse_url, {'category': 'vegetables'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('products', response.context)

        products = list(response.context['products'])
        self.assertGreaterEqual(len(products), 2)

        for product in products:
            self.assertTrue(
                hasattr(product, 'food_miles') or 'product_food_miles' in response.context,
                "Each browsed product should have food miles information available"
            )