from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import CustomUser
from marketplace.models import Product, Category


class TC011InventoryUpdateTests(TestCase):
    """
    Test Case ID: TC-011
    User Story: As a producer, I want to update my product inventory so that
    customers only see available products I have.
    """

    def setUp(self):
        self.client = Client()

        self.producer = CustomUser.objects.create_user(
            username='producer_tc011',
            email='producer_tc011@test.com',
            password='Password123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Jane',
            last_name='Smith'
        )

        self.other_producer = CustomUser.objects.create_user(
            username='other_producer_tc011',
            email='other_producer_tc011@test.com',
            password='Password123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Tom',
            last_name='Brown'
        )

        self.category = Category.objects.create(
            name='Vegetables',
            slug='vegetables',
            description='Fresh vegetables',
            is_active=True
        )

        self.tomatoes = Product.objects.create(
            producer=self.producer,
            category=self.category,
            name='Organic Tomatoes',
            description='Fresh local tomatoes',
            price=Decimal('3.50'),
            unit=Product.Unit.KG,
            stock_quantity=20,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.ALL_YEAR,
            allergen_info='No common allergens',
            harvest_date=None,
        )

        self.out_of_stock_item = Product.objects.create(
            producer=self.producer,
            category=self.category,
            name='Seasonal Courgettes',
            description='Local courgettes',
            price=Decimal('2.80'),
            unit=Product.Unit.KG,
            stock_quantity=0,
            is_available=False,
            seasonal_status=Product.SeasonalStatus.OUT_OF_SEASON,
            allergen_info='No common allergens',
            harvest_date=None,
        )

        self.other_producer_product = Product.objects.create(
            producer=self.other_producer,
            category=self.category,
            name='Other Producer Carrots',
            description='Not owned by producer_tc011',
            price=Decimal('2.20'),
            unit=Product.Unit.KG,
            stock_quantity=15,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
            allergen_info='No common allergens',
            harvest_date=None,
        )

        self.my_products_url = reverse('my_products')
        self.browse_url = reverse('browse')

    def _edit_url(self, product_id):
        return reverse('edit_product', args=[product_id])

    def _get_valid_edit_data(self, product, **overrides):
        data = {
            'name': product.name,
            'category': product.category.id,
            'description': product.description,
            'price': str(product.price),
            'unit': product.unit,
            'stock_quantity': product.stock_quantity,
            'seasonal_status': product.seasonal_status,
            'allergen_info': product.allergen_info or 'No common allergens',
            'harvest_date': product.harvest_date.isoformat() if product.harvest_date else '',
        }

        is_available = overrides.pop('is_available', product.is_available)
        data.update(overrides)

        if is_available:
            data['is_available'] = 'on'

        return data

    def test_producer_can_access_edit_page_for_own_product(self):
        self.client.login(username='producer_tc011', password='Password123!')

        response = self.client.get(self._edit_url(self.tomatoes.id))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Product')
        self.assertContains(response, 'Organic Tomatoes')

    def test_my_products_page_shows_edit_link(self):
        self.client.login(username='producer_tc011', password='Password123!')

        response = self.client.get(self.my_products_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'/browse/product/{self.tomatoes.id}/edit/')

    def test_producer_can_update_stock_quantity_and_availability(self):
        self.client.login(username='producer_tc011', password='Password123!')

        response = self.client.post(
            self._edit_url(self.tomatoes.id),
            data=self._get_valid_edit_data(
                self.tomatoes,
                stock_quantity=35,
                seasonal_status=Product.SeasonalStatus.IN_SEASON,
                is_available=True,
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'has been updated successfully')

        self.tomatoes.refresh_from_db()
        self.assertEqual(self.tomatoes.stock_quantity, 35)
        self.assertEqual(self.tomatoes.seasonal_status, Product.SeasonalStatus.IN_SEASON)
        self.assertTrue(self.tomatoes.is_available)

    def test_producer_cannot_edit_another_producers_product(self):
        self.client.login(username='producer_tc011', password='Password123!')

        response = self.client.get(self._edit_url(self.other_producer_product.id))

        self.assertEqual(response.status_code, 404)

    def test_negative_stock_update_rejected(self):
        self.client.login(username='producer_tc011', password='Password123!')

        response = self.client.post(
            self._edit_url(self.tomatoes.id),
            data=self._get_valid_edit_data(
                self.tomatoes,
                stock_quantity=-5,
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)
        self.assertIn('stock_quantity', response.context['form'].errors)
        self.assertFormError(
            response.context['form'],
            'stock_quantity',
            'Ensure this value is greater than or equal to 0.'
        )

        self.tomatoes.refresh_from_db()
        self.assertEqual(self.tomatoes.stock_quantity, 20)

    def test_unavailable_product_hidden_from_browse_after_update(self):
        self.client.login(username='producer_tc011', password='Password123!')

        self.client.post(
            self._edit_url(self.tomatoes.id),
            data=self._get_valid_edit_data(
                self.tomatoes,
                stock_quantity=0,
                is_available=False,
                seasonal_status=Product.SeasonalStatus.OUT_OF_SEASON,
            )
        )

        self.tomatoes.refresh_from_db()
        self.assertFalse(self.tomatoes.is_available)

        response = self.client.get(self.browse_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Organic Tomatoes')

    def test_product_reappears_in_browse_when_made_available_again(self):
        self.client.login(username='producer_tc011', password='Password123!')

        self.client.post(
            self._edit_url(self.out_of_stock_item.id),
            data=self._get_valid_edit_data(
                self.out_of_stock_item,
                stock_quantity=12,
                is_available=True,
                seasonal_status=Product.SeasonalStatus.IN_SEASON,
            )
        )

        self.out_of_stock_item.refresh_from_db()
        self.assertEqual(self.out_of_stock_item.stock_quantity, 12)
        self.assertTrue(self.out_of_stock_item.is_available)

        response = self.client.get(self.browse_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seasonal Courgettes')