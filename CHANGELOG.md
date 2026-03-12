# V1.0.0 - Alex McBride
- Initial commit
- Default Django setup
- Added info files for development
# V1.0.1 - Sebastian Macfarlane Woodley
- Added Basic homepage template
- Configured Template directory
- Wired homepage url
# V1.0.2 - Zain Malik
- Added Dockerfile
- Added docker-compose.yml
- Added requirements.txt
- Added start.sh
# V1.0.3 - Sebastian Macfarlane Woodley
- Began Html page design
- Began linking marketplace and accounts
# V1.0.4 - Alex McBride
- Setup view shells under marketplace and accounts. Merged with changes to views from main
# V1.0.5 - TJ
- Added marketplace/services/validators.py with 4 core validators
- Added marketplace/forms.py with ProductForm, CheckoutForm, OrderStatusForm
- Implemented 48-hour lead time validation
- Implemented UK postcode validation
- Implemented product data validation
- Implemented order status transition validation
# V1.0.6 - Sebastian Macfarlane Woodley
- Linked accounts and marketplace with real views and templates
- Wired up ProductForm and natively rendered Django fields in add_product.html
- Resolved server-side form validation bypass for pricing and hooked up UI error rendering
- Resolved silent UI failure by adding missing is_available flag to product form
- Configured WhiteNoise for static file serving in Docker
- Created pop_database.py to automatically seed food categories and test users
# V1.0.7 - Rob Howells
- Added custom user model for accounts and roles
- Created CustomUser with role field (customer/producer)
- Configured AUTH_USER_MODEL in settings
- Updated Django admin to display/manage user roles
- Created marketplace core models (Category and Product)
- Linked Product to producer user (FK relationship)
- Refactored templates to use shared static/css/main.css
# V1.0.8 - Rob Howells
- Created orders app backend (Cart/Checkout foundation)
- Added models: Cart, CartItem, Order, OrderItem
- Created and applied initial order migrations
- Added orders/urls.py and defined cart/checkout/order endpoints
- Wired orders into project
- Registered order models in Django admin
# V1.0.9 - Alex McBride
- Added Postgres DB integration via migration of structure to sqlite3 for now
- Added fixture to read/write saved data for population (can be loaded into local sqlite3 via: `Get-ChildItem marketplace/fixtures/*.json | ForEach-Object { python manage.py loaddata $_.FullName }` AFTER running migrate. Saved data can be overwritten via: `python manage.py dumpdata marketplace.Category --indent 2 > marketplace/fixtures/categories.json`, which will take from your local sqlite3 file) (EXTRA NOTE: different db models will have to be dumped separately, e.g. accounts being `python manage.py dumpdata accounts --indent 2 > marketplace/fixtures/accounts.json`.)
- Added .env.example (environment variable template)
- Added more migration files for models
- Extended models
- Registered models in admin panel
- Added 1 new dependency in requirements
# V1.0.10 - Sebastian Macfarlane Woodley
- Created HTML templates for cart and detail pages including editing and deleting products
- Added Cart Buttons to browse and product detail page
- Cart view shows all items with quantities, subtotals, and a total
- Users can update quantities or remove items
- Created product_detail view that returns product via product ID
- Edit view pre-fills product form with existing data. Validates on submit then saves
- Delete view shows confirm page on GET, Deletes on POST. Currently hard delete need to switch to soft delete
- Added cart buttons using POST form that sends product ID to add to cart view
- Cart uses Basket model, each BasketItem stores product and quantities
- Basket Get Total calculates sums all subtotals
- Users can remove items with POST requests
- Removed admin from registration role dropdown for security
- Added success confirmation message after registration
# V1.0.11 - Zain Malik
- Added GitHub Actions workflow files for collaboration and infrastructure pipeline scaffolding
- Implemented `collab.yml` to validate the Django project on push
- Configured collaboration workflow to support an easier team pull process using `main`
- Added placeholder `deploy.yml` workflow for future AWS infrastructure deployment
- Added placeholder `destroy.yml` workflow for future AWS infrastructure teardown
# V1.0.12 - Alex McBride
- Fixed role escalation vulnerability in registration: server-side whitelist now enforces only permitted roles (customer, producer, community_group, restaurant), admin role cannot be self-assigned via any client-side manipulation
- Added `clean_role` method to `CustomerRegistrationForm`, rejecting any non-whitelisted role at form validation level
- Fixed CSRF logout vulnerability: `logout_view` now requires POST (`@require_POST`): all logout links across all templates replaced with CSRF-token-protected POST forms (covers all 15 templates: accounts, marketplace, orders)
- Improved `add_product` access control: non-producers now receive `403 Forbidden` instead of a silent redirect
- Security review of merged code from main: confirmed all new orders views (`cart`, `checkout`, `order_detail`, `order_list`, `manage_orders`, `manage_order_detail`) are correctly guarded with `@login_required` and role checks (`_is_customer`, `_is_producer`), confirmed `edit_product` and `delete_product` use ownership-scoped `get_object_or_404` preventing cross-producer access
# V1.0.13 - Sebastian Macfarlane Woodley
- Expanded product model to match requirements of TC-003 , Seasonal Status, Allergen Info, Harvest Date
- Added Ability to add images  using pillow to handle image processing. Serves files locally
- Added My Products html page for producers to make managing stock, editing products and deleting products easier. Created my_products view using login required to ensure only producers can access their products. Code filters products to return products that match request.user. Orders by date
- Updated produt form to handle new fields  and edit and delete pages support adding images also
- Updated other templates to show new fields
# V1.0.14 - TJ
- Created REST API endpoints for marketplace data
- Added marketplace/api/serializers.py with ProductSerializer and CategorySerializer
- Added marketplace/api/views.py with ProductViewSet and CategoryViewSet (read-only)
- Added marketplace/api/urls.py with API routing using DRF routers
- Integrated API into main project URLs at /api/
- Configured REST Framework settings in settings.py (authentication, permissions, pagination)
- API supports filtering products by category, search term, and producer
- Implemented pagination (20 items per page) for product listings
- API endpoints: GET /api/products/, GET /api/categories/
- Provides JSON data for frontend JavaScript integration