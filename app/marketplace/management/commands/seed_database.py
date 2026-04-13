from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from marketplace.models import Category, Product

User = get_user_model()


class Command(BaseCommand):
    help = "Populate the database with sample categories, users, and products for testing."

    def handle(self, *args, **options):
        # ── Create Categories ──
        categories_data = [
            {"name": "Dairy", "slug": "dairy", "description": "Fresh milk, cheese, butter, and yogurt from local farms"},
            {"name": "Vegetables", "slug": "vegetables", "description": "Seasonal vegetables grown in the Bristol region"},
            {"name": "Fruit", "slug": "fruit", "description": "Fresh fruit from local orchards and farms"},
            {"name": "Meat", "slug": "meat", "description": "Ethically raised meat from local farms"},
            {"name": "Bakery", "slug": "bakery", "description": "Freshly baked bread, pastries, and cakes"},
            {"name": "Eggs", "slug": "eggs", "description": "Free-range eggs from local poultry farms"},
            {"name": "Honey & Preserves", "slug": "honey-preserves", "description": "Local honey, jams, and preserves"},
            {"name": "Drinks", "slug": "drinks", "description": "Locally produced juices, ciders, and soft drinks"},
        ]

        categories = {}
        for cat_data in categories_data:
            cat, created = Category.objects.get_or_create(
                slug=cat_data["slug"],
                defaults=cat_data,
            )
            categories[cat.slug] = cat
            status = "Created" if created else "Already exists"
            self.stdout.write(f"  {status}: Category '{cat.name}'")

        # ── Create Producer Users ──
        producers = {}
        producers_data = [
            {"username": "bristol_farm", "email": "farm@bristol.test", "first_name": "James", "last_name": "Hartley", "password": "testpass123"},
            {"username": "somerset_dairy", "email": "dairy@somerset.test", "first_name": "Emma", "last_name": "Clarke", "password": "testpass123"},
            {"username": "avon_bakery", "email": "bakery@avon.test", "first_name": "Tom", "last_name": "Baker", "password": "testpass123"},
        ]

        for p_data in producers_data:
            user, created = User.objects.get_or_create(
                username=p_data["username"],
                defaults={
                    "email": p_data["email"],
                    "first_name": p_data["first_name"],
                    "last_name": p_data["last_name"],
                    "role": "producer",
                    "delivery_address": "Bristol, UK",
                    "postcode": "BS1 1AA",
                },
            )
            if created:
                user.set_password(p_data["password"])
                user.save()
            producers[user.username] = user
            status = "Created" if created else "Already exists"
            self.stdout.write(f"  {status}: Producer '{user.username}'")

        # ── Create Customer User ──
        customer, created = User.objects.get_or_create(
            username="testcustomer",
            defaults={
                "email": "customer@test.com",
                "first_name": "Test",
                "last_name": "Customer",
                "role": "customer",
                "delivery_address": "10 High Street, Bristol",
                "postcode": "BS2 8HH",
            },
        )
        if created:
            customer.set_password("testpass123")
            customer.save()
        status = "Created" if created else "Already exists"
        self.stdout.write(f"  {status}: Customer '{customer.username}'")

        # ── Create Products ──
        today = date.today()
        products_data = [
            # Dairy
            {"name": "Whole Milk (1L)", "category": "dairy", "producer": "somerset_dairy", "price": "1.80", "unit": "l", "stock_quantity": 50, "description": "Fresh whole milk from grass-fed cows", "seasonal_status": "all_year", "allergen_info": "Contains milk"},
            {"name": "Semi-Skimmed Milk (1L)", "category": "dairy", "producer": "somerset_dairy", "price": "1.60", "unit": "l", "stock_quantity": 50, "description": "Semi-skimmed milk, perfect for everyday use", "seasonal_status": "all_year", "allergen_info": "Contains milk"},
            {"name": "Farmhouse Cheddar (200g)", "category": "dairy", "producer": "somerset_dairy", "price": "4.50", "unit": "pack", "stock_quantity": 30, "description": "Mature cheddar aged for 12 months", "seasonal_status": "all_year", "allergen_info": "Contains milk"},
            {"name": "Organic Butter (250g)", "category": "dairy", "producer": "somerset_dairy", "price": "3.20", "unit": "pack", "stock_quantity": 40, "description": "Rich creamy organic butter", "seasonal_status": "all_year", "allergen_info": "Contains milk"},
            {"name": "Natural Yogurt (500g)", "category": "dairy", "producer": "somerset_dairy", "price": "2.40", "unit": "pack", "stock_quantity": 25, "description": "Thick and creamy natural yogurt", "seasonal_status": "all_year", "allergen_info": "Contains milk"},

            # Vegetables
            {"name": "Carrots (1kg)", "category": "vegetables", "producer": "bristol_farm", "price": "1.20", "unit": "kg", "stock_quantity": 80, "description": "Crunchy organic carrots", "seasonal_status": "all_year"},
            {"name": "Potatoes (2kg)", "category": "vegetables", "producer": "bristol_farm", "price": "2.50", "unit": "kg", "stock_quantity": 60, "description": "Floury potatoes, great for roasting and mashing", "seasonal_status": "all_year"},
            {"name": "Broccoli", "category": "vegetables", "producer": "bristol_farm", "price": "1.50", "unit": "item", "stock_quantity": 40, "description": "Fresh green broccoli heads", "seasonal_status": "in_season"},
            {"name": "Tomatoes (500g)", "category": "vegetables", "producer": "bristol_farm", "price": "2.00", "unit": "pack", "stock_quantity": 35, "description": "Vine-ripened tomatoes", "seasonal_status": "in_season"},
            {"name": "Onions (1kg)", "category": "vegetables", "producer": "bristol_farm", "price": "1.00", "unit": "kg", "stock_quantity": 70, "description": "Brown onions, a kitchen staple", "seasonal_status": "all_year"},
            {"name": "Courgettes (3 pack)", "category": "vegetables", "producer": "bristol_farm", "price": "1.80", "unit": "pack", "stock_quantity": 30, "description": "Freshly picked courgettes", "seasonal_status": "in_season"},

            # Fruit
            {"name": "Apples - Bramley (6 pack)", "category": "fruit", "producer": "bristol_farm", "price": "2.80", "unit": "pack", "stock_quantity": 45, "description": "Cooking apples from local orchards", "seasonal_status": "in_season"},
            {"name": "Strawberries (400g)", "category": "fruit", "producer": "bristol_farm", "price": "3.50", "unit": "pack", "stock_quantity": 20, "description": "Sweet juicy strawberries", "seasonal_status": "limited"},
            {"name": "Raspberries (200g)", "category": "fruit", "producer": "bristol_farm", "price": "3.00", "unit": "pack", "stock_quantity": 15, "description": "Hand-picked raspberries", "seasonal_status": "limited"},

            # Meat
            {"name": "Chicken Breast (500g)", "category": "meat", "producer": "bristol_farm", "price": "6.50", "unit": "pack", "stock_quantity": 20, "description": "Free-range chicken breast fillets", "seasonal_status": "all_year"},
            {"name": "Pork Sausages (6 pack)", "category": "meat", "producer": "bristol_farm", "price": "4.80", "unit": "pack", "stock_quantity": 25, "description": "Traditional pork sausages made with local herbs", "seasonal_status": "all_year"},
            {"name": "Beef Mince (500g)", "category": "meat", "producer": "bristol_farm", "price": "5.50", "unit": "pack", "stock_quantity": 18, "description": "Lean beef mince from grass-fed cattle", "seasonal_status": "all_year"},
            {"name": "Lamb Chops (4 pack)", "category": "meat", "producer": "bristol_farm", "price": "8.00", "unit": "pack", "stock_quantity": 12, "description": "Tender lamb chops", "seasonal_status": "all_year"},

            # Bakery
            {"name": "Sourdough Loaf", "category": "bakery", "producer": "avon_bakery", "price": "3.80", "unit": "item", "stock_quantity": 20, "description": "Handmade sourdough with a crispy crust", "seasonal_status": "all_year", "allergen_info": "Contains gluten"},
            {"name": "Wholemeal Bread", "category": "bakery", "producer": "avon_bakery", "price": "2.50", "unit": "item", "stock_quantity": 25, "description": "Nutritious wholemeal loaf", "seasonal_status": "all_year", "allergen_info": "Contains gluten"},
            {"name": "Croissants (4 pack)", "category": "bakery", "producer": "avon_bakery", "price": "4.00", "unit": "pack", "stock_quantity": 15, "description": "Flaky butter croissants", "seasonal_status": "all_year", "allergen_info": "Contains gluten, milk, eggs"},
            {"name": "Scones (6 pack)", "category": "bakery", "producer": "avon_bakery", "price": "3.50", "unit": "pack", "stock_quantity": 18, "description": "Classic fruit scones", "seasonal_status": "all_year", "allergen_info": "Contains gluten, milk, eggs"},

            # Eggs
            {"name": "Free-Range Eggs (6 pack)", "category": "eggs", "producer": "bristol_farm", "price": "2.80", "unit": "pack", "stock_quantity": 40, "description": "Large free-range eggs from happy hens", "seasonal_status": "all_year", "allergen_info": "Contains eggs"},
            {"name": "Free-Range Eggs (12 pack)", "category": "eggs", "producer": "bristol_farm", "price": "4.80", "unit": "dozen", "stock_quantity": 30, "description": "Large free-range eggs, dozen box", "seasonal_status": "all_year", "allergen_info": "Contains eggs"},

            # Honey & Preserves
            {"name": "Local Wildflower Honey (340g)", "category": "honey-preserves", "producer": "bristol_farm", "price": "6.50", "unit": "item", "stock_quantity": 20, "description": "Raw wildflower honey from Bristol apiaries", "seasonal_status": "limited"},
            {"name": "Strawberry Jam (300g)", "category": "honey-preserves", "producer": "bristol_farm", "price": "3.80", "unit": "item", "stock_quantity": 25, "description": "Homemade strawberry jam", "seasonal_status": "all_year"},

            # Drinks
            {"name": "Apple Juice (1L)", "category": "drinks", "producer": "bristol_farm", "price": "3.20", "unit": "l", "stock_quantity": 30, "description": "Pressed from local Bramley apples", "seasonal_status": "in_season"},
            {"name": "Elderflower Cordial (500ml)", "category": "drinks", "producer": "bristol_farm", "price": "4.50", "unit": "ml", "stock_quantity": 20, "description": "Handmade elderflower cordial", "seasonal_status": "limited"},
        ]

        created_count = 0
        for p_data in products_data:
            cat = categories.get(p_data["category"])
            producer = producers.get(p_data["producer"])
            if not cat or not producer:
                continue

            _, created = Product.objects.get_or_create(
                producer=producer,
                name=p_data["name"],
                defaults={
                    "category": cat,
                    "price": Decimal(p_data["price"]),
                    "unit": p_data["unit"],
                    "stock_quantity": p_data["stock_quantity"],
                    "description": p_data["description"],
                    "is_available": True,
                    "seasonal_status": p_data["seasonal_status"],
                    "allergen_info": p_data.get("allergen_info", ""),
                    "harvest_date": today - timedelta(days=3),
                },
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDatabase seeded successfully!"
            f"\n  Categories: {len(categories_data)}"
            f"\n  Producers: {len(producers_data)}"
            f"\n  Products created: {created_count}"
            f"\n\nTest accounts:"
            f"\n  Customer: testcustomer / testpass123"
            f"\n  Producer: bristol_farm / testpass123"
            f"\n  Producer: somerset_dairy / testpass123"
            f"\n  Producer: avon_bakery / testpass123"
        ))
