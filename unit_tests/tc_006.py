from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from marketplace.models import Product, Category
from orders.models import Cart, CartItem


CustomUser = get_user_model()


class TC006ShoppingCartTests(TestCase):
    """
    Test Case ID: TC-006
    User Story: As a customer, I want to add products to my shopping cart so that I can purchase multiple items together.
    Description: Validates that customers can add products to a shopping cart, modify quantities, and view cart contents before proceeding to checkout.
    """

    def setUp(self):
        self.client = Client()

        # 1. Create a customer
        self.customer = CustomUser.objects.create_user(
            username='test_customer',
            email='customer@test.com',
            password='Password123!',
            role=CustomUser.Role.CUSTOMER
        )

        # 2. Create a producer
        self.producer = CustomUser.objects.create_user(
            username='test_producer',
            email='producer@test.com',
            password='Password123!',
            role=CustomUser.Role.PRODUCER
        )

        # 3. Create a category
        self.category = Category.objects.create(
            name='Fresh Produce',
            slug='fresh-produce'
        )

        # 4. Create Product 1: Organic Carrots
        self.carrots = Product.objects.create(
            producer=self.producer,
            category=self.category,
            name='Organic Carrots',
            description='Fresh local organic carrots.',
            price=Decimal('2.50'),
            unit=Product.Unit.KG,
            stock_quantity=50,
            is_available=True
        )

        # 5. Create Product 2: Fresh Milk
        self.milk = Product.objects.create(
            producer=self.producer,
            category=self.category,
            name='Fresh Milk',
            description='Whole milk from local dairy.',
            price=Decimal('1.80'),
            unit=Product.Unit.L,
            stock_quantity=20,
            is_available=True
        )

    def test_tc006_shopping_cart_workflow(self):
        """
        Executes the exact test steps from TC-006 definition.
        """
        # Precondition: Customer is logged in
        self.client.login(username='test_customer', password='Password123!')

        # Steps 1-4: Select 2kg Organic Carrots and Click 'Add to Cart'
        referer_url_1 = f'/browse/product/{self.carrots.id}/'
        response = self.client.post(reverse('orders:add_to_cart', args=[self.carrots.id]), {'quantity': 2}, HTTP_REFERER=referer_url_1)
        
        # Step 5: Observe confirmation (Redirects back to product page)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, referer_url_1, fetch_redirect_response=False)

        # Steps 6-8: Select 3 litres of Fresh Milk and Click 'Add to Cart'
        referer_url_2 = f'/browse/product/{self.milk.id}/'
        response = self.client.post(reverse('orders:add_to_cart', args=[self.milk.id]), {'quantity': 3}, HTTP_REFERER=referer_url_2)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, referer_url_2, fetch_redirect_response=False)
        
        # Steps 9-10: View cart contents and verify correct quantities and prices
        cart = Cart.objects.get(user=self.customer, status=Cart.STATUS_ACTIVE)
        self.assertEqual(cart.items.count(), 2)

        carrot_item = cart.items.get(product=self.carrots)
        self.assertEqual(carrot_item.quantity, 2)
        self.assertEqual(carrot_item.line_total, Decimal('5.00')) # 2.50 * 2

        milk_item = cart.items.get(product=self.milk)
        self.assertEqual(milk_item.quantity, 3)
        self.assertEqual(milk_item.line_total, Decimal('5.40')) # 1.80 * 3
        
        # Verify cart total across all vendor items
        self.assertEqual(cart.total, Decimal('10.40'))

        # Step 11: Modify quantity of Organic Carrots to 3 kg
        response = self.client.post(reverse('orders:update_cart_item', args=[carrot_item.id]), {'quantity': 3})
        self.assertEqual(response.status_code, 302)

        # Step 12: Observe updated total price
        cart.refresh_from_db()
        carrot_item.refresh_from_db()
        
        # Price calculations are accurate after update
        self.assertEqual(carrot_item.quantity, 3)
        self.assertEqual(carrot_item.line_total, Decimal('7.50')) # 2.50 * 3
        self.assertEqual(cart.total, Decimal('12.90')) # 7.50 + 5.40

        # Verify items can be removed from cart (Acceptance Criteria)
        response = self.client.post(reverse('orders:remove_cart_item', args=[milk_item.id]))
        self.assertEqual(response.status_code, 302)
        
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.total, Decimal('7.50'))
