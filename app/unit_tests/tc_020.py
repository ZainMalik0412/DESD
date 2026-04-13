from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import CustomUser
from marketplace.models import Product, Category, Recipe, RecipeProduct, FarmStory, FavoriteRecipe
from marketplace.forms import RecipeForm, FarmStoryForm


class TC020ProducerContentSharingTests(TestCase):
    """
    Test Case ID: TC-020
    User Story: As a producer, I want to share recipes and farm stories so that I can 
    engage with the community and educate customers.
    """

    def setUp(self):
        self.client = Client()

        # Create producer
        self.producer = CustomUser.objects.create_user(
            username='producer_tc020',
            email='producer_tc020@test.com',
            password='Password123!',
            role=CustomUser.Role.PRODUCER,
            first_name='Jane',
            last_name='Farmer'
        )

        # Create customer
        self.customer = CustomUser.objects.create_user(
            username='customer_tc020',
            email='customer_tc020@test.com',
            password='Password123!',
            role=CustomUser.Role.CUSTOMER,
            first_name='Chris',
            last_name='Buyer'
        )

        # Create category
        self.vegetables = Category.objects.create(
            name='Vegetables',
            slug='vegetables',
            description='Fresh vegetables',
            is_active=True
        )

        # Create products for recipe linking (Steps 5)
        self.carrots = Product.objects.create(
            producer=self.producer,
            category=self.vegetables,
            name='Carrots',
            description='Fresh organic carrots',
            price=Decimal('2.50'),
            unit=Product.Unit.KG,
            stock_quantity=20,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
            allergen_info='No common allergens'
        )

        self.parsnips = Product.objects.create(
            producer=self.producer,
            category=self.vegetables,
            name='Parsnips',
            description='Organic parsnips',
            price=Decimal('2.80'),
            unit=Product.Unit.KG,
            stock_quantity=15,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.IN_SEASON,
            allergen_info='No common allergens'
        )

        self.potatoes = Product.objects.create(
            producer=self.producer,
            category=self.vegetables,
            name='Potatoes',
            description='Fresh potatoes',
            price=Decimal('1.90'),
            unit=Product.Unit.KG,
            stock_quantity=30,
            is_available=True,
            seasonal_status=Product.SeasonalStatus.ALL_YEAR,
            allergen_info='No common allergens'
        )

        # URLs
        self.add_recipe_url = reverse('add_recipe')
        self.my_recipes_url = reverse('my_recipes')
        self.add_story_url = reverse('add_story')
        self.my_stories_url = reverse('my_stories')
        self.producer_profile_url = reverse('producer_profile', args=[self.producer.id])

    def _login_producer(self):
        """Helper to login as producer."""
        self.client.login(username='producer_tc020', password='Password123!')

    def _login_customer(self):
        """Helper to login as customer."""
        self.client.login(username='customer_tc020', password='Password123!')

    def test_producer_can_navigate_to_add_recipe_section(self):
        """
        Steps 1-2:
        Navigate to 'Content' or 'Farm Stories' section
        Click 'Add New Recipe'
        """
        self._login_producer()
        response = self.client.get(self.add_recipe_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add New Recipe')
        self.assertContains(response, 'Recipe Title')

    def test_producer_can_create_recipe_with_details(self):
        """
        Steps 3-9:
        Enter recipe title, description, ingredients, instructions,
        link products, upload image, add seasonal tag, and publish
        """
        self._login_producer()

        recipe_data = {
            'title': 'Roasted Root Vegetable Medley',
            'description': 'A delicious autumn recipe using seasonal root vegetables.',
            'ingredients': '- 500g Carrots\n- 300g Parsnips\n- 400g Potatoes\n- Olive oil\n- Salt and pepper',
            'instructions': '1. Preheat oven to 200°C\n2. Chop vegetables into chunks\n3. Toss with oil\n4. Roast for 40 minutes',
            'seasonal_tag': 'autumn_winter',
            'is_published': True,
            'linked_products': [self.carrots.id, self.parsnips.id, self.potatoes.id]
        }

        response = self.client.post(self.add_recipe_url, recipe_data)

        # Should redirect or show success
        self.assertTrue(response.status_code in [200, 302])

        # Verify recipe was created
        recipe = Recipe.objects.filter(title='Roasted Root Vegetable Medley').first()
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe.producer, self.producer)
        self.assertEqual(recipe.seasonal_tag, 'autumn_winter')
        self.assertTrue(recipe.is_published)

        # Verify products are linked
        linked_product_ids = list(recipe.linked_products.values_list('product_id', flat=True))
        self.assertIn(self.carrots.id, linked_product_ids)
        self.assertIn(self.parsnips.id, linked_product_ids)
        self.assertIn(self.potatoes.id, linked_product_ids)

    def test_producer_can_create_farm_story(self):
        """
        Steps 10-12:
        Create farm story post about harvest season,
        add photos, and publish story
        """
        self._login_producer()

        story_data = {
            'title': 'Harvest Season at the Farm',
            'content': 'This autumn has been particularly bountiful. Our root vegetables have thrived in the cooler weather, and we\'re excited to share the harvest with our community.',
            'is_published': True
        }

        response = self.client.post(self.add_story_url, story_data)

        # Should redirect or show success
        self.assertTrue(response.status_code in [200, 302])

        # Verify story was created
        story = FarmStory.objects.filter(title='Harvest Season at the Farm').first()
        self.assertIsNotNone(story)
        self.assertEqual(story.producer, self.producer)
        self.assertTrue(story.is_published)

    def test_recipe_appears_on_linked_product_pages(self):
        """
        Steps 13-16:
        Log in as customer, view product page for Carrots,
        observe 'Recipe Suggestions' section showing linked recipes,
        click through to view full recipe
        """
        # Create a published recipe linked to carrots
        recipe = Recipe.objects.create(
            producer=self.producer,
            title='Roasted Root Vegetable Medley',
            description='Delicious root vegetables',
            ingredients='Carrots, Parsnips, Potatoes',
            instructions='Roast them all together',
            seasonal_tag='autumn_winter',
            is_published=True
        )
        RecipeProduct.objects.create(recipe=recipe, product=self.carrots)

        self._login_customer()

        # View product detail page
        product_url = reverse('product_detail', args=[self.carrots.id])
        response = self.client.get(product_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recipe Suggestions')
        self.assertContains(response, 'Roasted Root Vegetable Medley')

        # Click through to recipe detail
        recipe_url = reverse('recipe_detail', args=[recipe.id])
        recipe_response = self.client.get(recipe_url)

        self.assertEqual(recipe_response.status_code, 200)
        self.assertContains(recipe_response, 'Roasted Root Vegetable Medley')
        self.assertContains(recipe_response, recipe.instructions)

    def test_farm_stories_visible_on_producer_profile(self):
        """
        Steps 17-18:
        Navigate to producer profile page,
        view farm stories and educational content
        """
        # Create published story
        story = FarmStory.objects.create(
            producer=self.producer,
            title='Harvest Season at the Farm',
            content='This autumn has been particularly bountiful.',
            is_published=True
        )

        self._login_customer()
        response = self.client.get(self.producer_profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Harvest Season at the Farm')
        self.assertContains(response, 'Farm Stories')

    def test_recipe_format_is_user_friendly(self):
        """
        Acceptance Criteria:
        Recipe format is user-friendly and readable
        """
        recipe = Recipe.objects.create(
            producer=self.producer,
            title='Simple Carrot Soup',
            description='Easy and nutritious',
            ingredients='- 1kg Carrots\n- 1L Vegetable stock',
            instructions='1. Chop carrots\n2. Simmer in stock\n3. Blend until smooth',
            seasonal_tag='all_season',
            is_published=True
        )

        self._login_customer()
        recipe_url = reverse('recipe_detail', args=[recipe.id])
        response = self.client.get(recipe_url)

        self.assertEqual(response.status_code, 200)
        # Check that recipe sections are present
        self.assertContains(response, 'Ingredients')
        self.assertContains(response, 'Instructions')
        self.assertContains(response, 'Simple Carrot Soup')

    def test_product_links_in_recipes_are_clickable(self):
        """
        Acceptance Criteria:
        Product links are clickable and lead to purchase options
        """
        recipe = Recipe.objects.create(
            producer=self.producer,
            title='Carrot Cake',
            description='Delicious cake',
            ingredients='Carrots, flour, sugar',
            instructions='Mix and bake',
            seasonal_tag='all_season',
            is_published=True
        )
        RecipeProduct.objects.create(recipe=recipe, product=self.carrots)

        self._login_customer()
        recipe_url = reverse('recipe_detail', args=[recipe.id])
        response = self.client.get(recipe_url)

        self.assertEqual(response.status_code, 200)
        # Check for product link
        product_url = reverse('product_detail', args=[self.carrots.id])
        self.assertContains(response, product_url)
        self.assertContains(response, 'Carrots')

    def test_customers_can_access_educational_content_easily(self):
        """
        Acceptance Criteria:
        Customers can access educational content easily
        """
        # Create recipe and story
        recipe = Recipe.objects.create(
            producer=self.producer,
            title='Root Vegetable Guide',
            description='Learn about root vegetables',
            ingredients='Various root vegetables',
            instructions='Preparation guide',
            seasonal_tag='autumn_winter',
            is_published=True
        )

        story = FarmStory.objects.create(
            producer=self.producer,
            title='About Our Farm',
            content='We are a family-run organic farm.',
            is_published=True
        )

        self._login_customer()

        # Access via producer profile
        response = self.client.get(self.producer_profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Root Vegetable Guide')
        self.assertContains(response, 'About Our Farm')

    def test_seasonal_tags_help_organise_content(self):
        """
        Acceptance Criteria:
        Seasonal tags help organise content
        """
        # Create recipes with different seasonal tags
        autumn_recipe = Recipe.objects.create(
            producer=self.producer,
            title='Autumn Harvest Stew',
            description='Perfect for autumn',
            ingredients='Root vegetables',
            instructions='Slow cook',
            seasonal_tag='autumn_winter',
            is_published=True
        )

        summer_recipe = Recipe.objects.create(
            producer=self.producer,
            title='Summer Salad',
            description='Light and fresh',
            ingredients='Fresh vegetables',
            instructions='Toss together',
            seasonal_tag='summer',
            is_published=True
        )

        self._login_customer()

        # Check recipes show seasonal tags
        autumn_url = reverse('recipe_detail', args=[autumn_recipe.id])
        response = self.client.get(autumn_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Autumn')

    def test_content_strengthens_producer_customer_connection(self):
        """
        Acceptance Criteria:
        Content strengthens producer-customer connection
        """
        # Create both recipe and story
        recipe = Recipe.objects.create(
            producer=self.producer,
            title='Family Recipe',
            description='Passed down through generations',
            ingredients='Seasonal vegetables',
            instructions='Cook with love',
            seasonal_tag='all_season',
            is_published=True
        )

        story = FarmStory.objects.create(
            producer=self.producer,
            title='Our Family Story',
            content='We have been farming this land for three generations.',
            is_published=True
        )

        self._login_customer()

        # Verify both are accessible on producer profile
        response = self.client.get(self.producer_profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.producer.first_name)
        self.assertContains(response, 'Family Recipe')
        self.assertContains(response, 'Our Family Story')

    def test_unpublished_recipes_not_visible_to_customers(self):
        """
        Additional test: Unpublished content should not be visible to customers
        """
        draft_recipe = Recipe.objects.create(
            producer=self.producer,
            title='Draft Recipe',
            description='Not ready yet',
            ingredients='TBD',
            instructions='TBD',
            seasonal_tag='all_season',
            is_published=False
        )

        self._login_customer()

        # Try to access draft recipe directly
        recipe_url = reverse('recipe_detail', args=[draft_recipe.id])
        response = self.client.get(recipe_url)

        # Should get 404 or redirect since recipe is not published
        self.assertNotEqual(response.status_code, 200)

    def test_producer_can_edit_existing_recipe(self):
        """
        Additional test: Producer should be able to edit their recipes
        """
        recipe = Recipe.objects.create(
            producer=self.producer,
            title='Original Title',
            description='Original description',
            ingredients='Original ingredients',
            instructions='Original instructions',
            seasonal_tag='all_season',
            is_published=False
        )

        self._login_producer()

        edit_url = reverse('edit_recipe', args=[recipe.id])
        response = self.client.get(edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Original Title')

        # Update the recipe
        updated_data = {
            'title': 'Updated Title',
            'description': 'Updated description',
            'ingredients': 'Updated ingredients',
            'instructions': 'Updated instructions',
            'seasonal_tag': 'spring',
            'is_published': True
        }

        response = self.client.post(edit_url, updated_data)
        self.assertTrue(response.status_code in [200, 302])

        # Verify changes
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, 'Updated Title')
        self.assertEqual(recipe.seasonal_tag, 'spring')
        self.assertTrue(recipe.is_published)

    def test_producer_can_delete_recipe(self):
        """
        Additional test: Producer should be able to delete their recipes
        """
        recipe = Recipe.objects.create(
            producer=self.producer,
            title='Recipe to Delete',
            description='Will be deleted',
            ingredients='Items',
            instructions='Steps',
            seasonal_tag='all_season',
            is_published=False
        )

        self._login_producer()

        delete_url = reverse('delete_recipe', args=[recipe.id])
        response = self.client.post(delete_url)

        # Should redirect after deletion
        self.assertEqual(response.status_code, 302)

        # Verify recipe is deleted
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_customers_can_save_favourite_recipes(self):
        """
        Acceptance Criteria:
        Customers can save favourite recipes
        """
        # Create a published recipe
        recipe = Recipe.objects.create(
            producer=self.producer,
            title='Delicious Recipe',
            description='A tasty recipe',
            ingredients='Some ingredients',
            instructions='Cook it well',
            seasonal_tag='all_season',
            is_published=True
        )

        self._login_customer()

        # Save the recipe as favorite
        toggle_url = reverse('toggle_favorite_recipe', args=[recipe.id])
        response = self.client.post(toggle_url)

        # Should redirect back to recipe
        self.assertTrue(response.status_code in [200, 302])

        # Verify recipe is saved
        self.assertTrue(FavoriteRecipe.objects.filter(user=self.customer, recipe=recipe).exists())

        # Access saved recipes page
        favorites_url = reverse('my_favorite_recipes')
        response = self.client.get(favorites_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delicious Recipe')

    def test_customers_can_unsave_favourite_recipes(self):
        """
        Additional test: Customers should be able to remove recipes from favorites
        """
        # Create a published recipe and favorite it
        recipe = Recipe.objects.create(
            producer=self.producer,
            title='Recipe to Unsave',
            description='A recipe',
            ingredients='Ingredients',
            instructions='Instructions',
            seasonal_tag='all_season',
            is_published=True
        )

        FavoriteRecipe.objects.create(user=self.customer, recipe=recipe)

        self._login_customer()

        # Unsave the recipe
        toggle_url = reverse('toggle_favorite_recipe', args=[recipe.id])
        response = self.client.post(toggle_url)

        # Should redirect
        self.assertTrue(response.status_code in [200, 302])

        # Verify recipe is no longer saved
        self.assertFalse(FavoriteRecipe.objects.filter(user=self.customer, recipe=recipe).exists())

    def test_favorite_button_shows_correct_state(self):
        """
        Additional test: Recipe detail page should show correct favorite button state
        """
        # Create a published recipe
        recipe = Recipe.objects.create(
            producer=self.producer,
            title='Test Recipe',
            description='Test',
            ingredients='Test ingredients',
            instructions='Test instructions',
            seasonal_tag='all_season',
            is_published=True
        )

        self._login_customer()

        # View recipe - should show "Save Recipe" button
        recipe_url = reverse('recipe_detail', args=[recipe.id])
        response = self.client.get(recipe_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Save Recipe')

        # Favorite the recipe
        FavoriteRecipe.objects.create(user=self.customer, recipe=recipe)

        # View recipe again - should show "Saved to Favorites" button
        response = self.client.get(recipe_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Saved to Favorites')


    def test_content_moderation_rejects_inappropriate_recipe(self):
        """
        Acceptance Criteria:
        Content is appropriately moderated - inappropriate content in recipes should be rejected
        """
        self._login_producer()

        # Try to create recipe with inappropriate content
        inappropriate_data = {
            'title': 'Test Recipe with inappropriate fuck word',
            'description': 'A normal description',
            'ingredients': '- 500g Carrots\n- Salt',
            'instructions': 'Cook them properly',
            'seasonal_tag': 'all_season',
            'is_published': False
        }

        response = self.client.post(self.add_recipe_url, inappropriate_data)

        # Should show validation error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'inappropriate or prohibited content')

        # Verify recipe was NOT created
        self.assertFalse(Recipe.objects.filter(title__icontains='inappropriate').exists())

    def test_content_moderation_rejects_spam_recipe(self):
        """
        Acceptance Criteria:
        Content is appropriately moderated - spam patterns in recipes should be rejected
        """
        self._login_producer()

        # Try to create recipe with spam-like repetition
        spam_data = {
            'title': 'Buy Buy Buy Buy Buy Buy Buy Buy Buy Buy Buy Recipe',
            'description': 'Normal description here',
            'ingredients': '- Ingredients here',
            'instructions': 'Instructions here',
            'seasonal_tag': 'all_season',
            'is_published': False
        }

        response = self.client.post(self.add_recipe_url, spam_data)

        # Should show validation error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'spam')

    def test_content_moderation_rejects_inappropriate_farm_story(self):
        """
        Acceptance Criteria:
        Content is appropriately moderated - inappropriate content in farm stories should be rejected
        """
        self._login_producer()

        # Try to create story with inappropriate content
        inappropriate_story = {
            'title': 'Our Farm Story',
            'content': 'This is a story with inappropriate fuck spam content that should be rejected.',
            'is_published': False
        }

        response = self.client.post(self.add_story_url, inappropriate_story)

        # Should show validation error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'inappropriate or prohibited content')

        # Verify story was NOT created
        self.assertFalse(FarmStory.objects.filter(content__icontains='fuck').exists())

    def test_content_moderation_accepts_appropriate_content(self):
        """
        Acceptance Criteria:
        Content moderation allows appropriate, family-friendly content
        """
        self._login_producer()

        # Create recipe with appropriate content
        appropriate_data = {
            'title': 'Delicious Autumn Harvest Recipe',
            'description': 'A wonderful seasonal recipe perfect for family dinners',
            'ingredients': '- 500g Fresh organic carrots\n- 300g Parsnips\n- 2 tablespoons olive oil\n- Salt and pepper to taste',
            'instructions': 'Preheat oven to 200C. Chop vegetables into even pieces. Toss with oil. Roast for 40 minutes until golden.',
            'seasonal_tag': 'autumn_winter',
            'is_published': True
        }

        response = self.client.post(self.add_recipe_url, appropriate_data)

        # Should succeed (redirect or 200)
        self.assertTrue(response.status_code in [200, 302])

        # Verify recipe was created
        recipe = Recipe.objects.filter(title='Delicious Autumn Harvest Recipe').first()
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe.producer, self.producer)

    def test_content_moderation_rejects_excessive_capitalisation(self):
        """
        Acceptance Criteria:
        Content moderation rejects spam-like excessive capitalisation
        """
        self._login_producer()

        # Try to create recipe with excessive caps (shouting/spam pattern)
        caps_data = {
            'title': 'AMAZING RECIPE YOU MUST TRY NOW!!!',
            'description': 'BEST RECIPE EVER MADE IN HISTORY',
            'ingredients': 'CARROTS AND OTHER VEGETABLES',
            'instructions': 'COOK EVERYTHING AT HIGH HEAT IMMEDIATELY',
            'seasonal_tag': 'all_season',
            'is_published': False
        }

        response = self.client.post(self.add_recipe_url, caps_data)

        # Should show validation error for excessive capitalisation
        self.assertEqual(response.status_code, 200)
        # Check for either capitalisation or spam-related error
        self.assertTrue(
            'excessive capitalisation' in response.content.decode().lower() or 
            'spam' in response.content.decode().lower() or
            'inappropriate' in response.content.decode().lower()
        )
