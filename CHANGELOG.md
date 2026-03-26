# V1.0.0 - Alex McBride
- Initial commit
- Default Django setup
- Added info files for development
# V1.0.1 - Sebastian Macfarlane Woodley
- Added Basic homepage template
- Configured Template directory
- Wired homepage url
# V1.0.2 - Zain Malik
- Added Dockerfile with multi-stage build for a lightweight production image
- Added start.sh entrypoint script to handle database readiness, migrations, and static files
- Added requirements.txt with all project dependencies
- Configured Gunicorn as the production web server
# V1.0.3 - Zain Malik
- Added docker-compose.yml to run the app and MySQL database together
- Configured MySQL 8.0 service with persistent storage and healthchecks
- Set up environment variables for database, Django, and Stripe configuration
- Mapped port 8000 for local development access
# V1.0.4 - Sebastian Macfarlane Woodley
- Began Html page design
- Began linking marketplace and accounts
# V1.0.5 - Alex McBride
- Setup view shells under marketplace and accounts. Merged with changes to views from main
# V1.0.6 - TJ
- Added marketplace/services/validators.py with 4 core validators
- Added marketplace/forms.py with ProductForm, CheckoutForm, OrderStatusForm
- Implemented 48-hour lead time validation
- Implemented UK postcode validation
- Implemented product data validation
- Implemented order status transition validation
# V1.0.7 - Sebastian Macfarlane Woodley
- Linked accounts and marketplace with real views and templates
- Wired up ProductForm and natively rendered Django fields in add_product.html
- Resolved server-side form validation bypass for pricing and hooked up UI error rendering
- Resolved silent UI failure by adding missing is_available flag to product form
- Configured WhiteNoise for static file serving in Docker
- Created pop_database.py to automatically seed food categories and test users
# V1.0.8 - Rob Howells
- Added custom user model for accounts and roles
- Created CustomUser with role field (customer/producer)
- Configured AUTH_USER_MODEL in settings
- Updated Django admin to display/manage user roles
- Created marketplace core models (Category and Product)
- Linked Product to producer user (FK relationship)
- Refactored templates to use shared static/css/main.css
# V1.0.9 - Rob Howells
- Created orders app backend (Cart/Checkout foundation)
- Added models: Cart, CartItem, Order, OrderItem
- Created and applied initial order migrations
- Added orders/urls.py and defined cart/checkout/order endpoints
- Wired orders into project
- Registered order models in Django admin
# V1.0.10 - Alex McBride
- Added Postgres DB integration via migration of structure to sqlite3 for now
- Added fixture to read/write saved data for population (can be loaded into local sqlite3 via: `Get-ChildItem marketplace/fixtures/*.json | ForEach-Object { python manage.py loaddata $_.FullName }` AFTER running migrate. Saved data can be overwritten via: `python manage.py dumpdata marketplace.Category --indent 2 > marketplace/fixtures/categories.json`, which will take from your local sqlite3 file) (EXTRA NOTE: different db models will have to be dumped separately, e.g. accounts being `python manage.py dumpdata accounts --indent 2 > marketplace/fixtures/accounts.json`.)
- Added .env.example (environment variable template)
- Added more migration files for models
- Extended models
- Registered models in admin panel
- Added 1 new dependency in requirements
# V1.0.11 - Sebastian Macfarlane Woodley
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
# V1.0.12 - Zain Malik
- Added GitHub Actions workflow files for collaboration and infrastructure pipeline scaffolding
- Implemented `collab.yml` to validate the Django project on push
- Configured collaboration workflow to support an easier team pull process using `main`
- Added placeholder `deploy.yml` workflow for future AWS infrastructure deployment
- Added placeholder `destroy.yml` workflow for future AWS infrastructure teardown
# V1.0.13 - Alex McBride
- Fixed role escalation vulnerability in registration: server-side whitelist now enforces only permitted roles (customer, producer, community_group, restaurant), admin role cannot be self-assigned via any client-side manipulation
- Added `clean_role` method to `CustomerRegistrationForm`, rejecting any non-whitelisted role at form validation level
- Fixed CSRF logout vulnerability: `logout_view` now requires POST (`@require_POST`): all logout links across all templates replaced with CSRF-token-protected POST forms (covers all 15 templates: accounts, marketplace, orders)
- Improved `add_product` access control: non-producers now receive `403 Forbidden` instead of a silent redirect
- Security review of merged code from main: confirmed all new orders views (`cart`, `checkout`, `order_detail`, `order_list`, `manage_orders`, `manage_order_detail`) are correctly guarded with `@login_required` and role checks (`_is_customer`, `_is_producer`), confirmed `edit_product` and `delete_product` use ownership-scoped `get_object_or_404` preventing cross-producer access
# V1.0.14 - Sebastian Macfarlane Woodley
- Expanded product model to match requirements of TC-003 , Seasonal Status, Allergen Info, Harvest Date
- Added Ability to add images  using pillow to handle image processing. Serves files locally
- Added My Products html page for producers to make managing stock, editing products and deleting products easier. Created my_products view using login required to ensure only producers can access their products. Code filters products to return products that match request.user. Orders by date
- Updated produt form to handle new fields  and edit and delete pages support adding images also
- Updated other templates to show new fields
# V1.0.15 - TJ
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
# V1.0.16 - Rob Howells
- Added Terms page template
- Added Terms page view in brfn_app/views.py
- Added URL route for Terms page
- Updated registration page to link to Terms page
- Improved registration form styling in main.css
- Tidied navigation/page flow for account signup
# V1.0.17 - Zain Malik
- Integrated Stripe Checkout test-mode payment flow into the orders app
- Updated checkout to redirect to Stripe and handle success/cancel return pages
- Added Stripe configuration to project settings, environment template, and docker-compose
- Added a database seed command for sample categories, users, and products
- Populated test data to support end to end checkout testing with sample items
# V1.0.18 - Alex McBride
- Added test cases 1-5
# V1.0.19 - Sebastian Macfarlane Woodley
- Added test cases 6-10
# V1.0.20 - Rob Howells
- Added test cases 11-15
# V1.0.21 - Rob Howells
- Updated product edit/update flow so producer stock and availability changes save correctly
- Fixed inventory update behaviour so unavailable products are hidden from browse and reappear when made available again
- Improved product form validation for stock updates and allergen information
- Updated browse search to also match allergen information
- Added allergen filter to browse page with options for all products/has allergens/no allergens
- Added allergen information on display browse cards
- Added clearer allergen warning/no common allergens display on product detail pages
- Added food miles calculation to browse page for logged-in customers with postcode data
- Added food miles display to product detail pages
- Added food miles display per cart item and total food miles summary in cart
- Updated cart view context to support food miles data used by TC-013 tests
- Confirmed TC-011, TC-013 and TC-015 now passing
# V1.0.22 - TJ
- Created REST API endpoints for shopping cart operations
- Added orders/api/serializers.py with CartSerializer, CartItemSerializer, OrderSerializer
- Added orders/api/views.py with CartViewSet and OrderViewSet
- Added orders/api/urls.py with API routing
- Integrated cart API into main project URLs at /api/cart/ and /api/orders/
- API endpoints: GET/POST /api/cart/, POST /api/cart/add_item/, PATCH /api/cart/update_item/{id}/, DELETE /api/cart/remove_item/{id}/, POST /api/cart/clear/
- API uses same Cart/CartItem models as HTML views, ensuring data consistency
- All cart API endpoints require authentication
- Provides JSON interface for frontend JavaScript and mobile app integration
# V1.0.23 - Rob Howells
- Added organic certification status to products
- Let producers set organic certification when creating/editing listings
- Added organic certification filter on browse page
- Displayed certification status on browse cards and product detail page
- Completed TC-014 and got all related tests passing
# V1.0.24 - Zain Malik
- Integrated email notifications for order status updates using Django built-in email
- Created orders/notifications.py with send_order_confirmation_email() and send_status_update_email()
- Order confirmation email sent to customer after successful Stripe payment
- Status update email sent to customer when producer changes order status
- Added email configuration to settings.py with console backend (development) and Gmail SMTP (production)
- Updated .env.example and docker-compose.yml with email environment variables
# V1.0.25 - Rob Howells
- Added producer Payments page
- Added downloadable CSV payment report
- Added weekly settlement summary for producers
- Showed total orders value, commision, producer payment, payment status, and tax year total
- Limited settlements to delivered orders from the previous completed weel
- Created payments.html and moved payments page out of raw inline HTML
- Added Payments link to producer navigation
- Merged email notification changes with existing orders/views.py work
- Kept order confirmation and status update email functions in place
# V1.0.26 - Zain Malik
- Added dedicated run-tests job to collab.yml CI/CD pipeline
- Pipeline now runs all 15 unit tests as a separate jobs
- Merge to main is now gated on test cases passing — code only merges if all tests succeed
- Restructured pipeline flow: build-and-validate → run-tests → merge-to-main
# V1.0.27 - Alex McBride
- Fixed missing image validators - added file extension, size (5MB max), and content-type validation to Product.image field
- Fixed email injection vulnerability - sanitised all user input in email notifications to prevent header injection attacks
- Fixed CSV injection vulnerability - sanitised CSV export data to prevent formula execution in Excel
- Added API rate limiting - anonymous users: 100/hour, authenticated users: 1000/hour
- Enhanced password hashing - configured Argon2 as primary password hasher (stronger than default PBKDF2)
- Added security headers - `SESSION_COOKIE_HTTPONLY`, `CSRF_COOKIE_HTTPONLY`, `SECURE_BROWSER_XSS_FILTER`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS`
- Added `FILE_UPLOAD_MAX_MEMORY_SIZE` limit of 5MB to match image validators
- Enforced minimum password length of 8 characters
- Created marketplace/services/file_validators.py with image validation functions
- Cleaned up duplicate configuration entries in settings.py (`REST_FRAMEWORK`, `STATIC_URL`)
- Fixed test cases to support Argon2 password hashing (tc_001, tc_002)
- Added Stripe API mocking to checkout tests (tc_007, tc_008, tc_009) to prevent live API calls during testing
- All security fixes apply without breaking existing functionality
- Expanded food miles calculation system with comprehensive postcode database
- Added 25+ postcode coordinates covering Bristol area (BS1-BS49)
- Food miles now calculated using Haversine formula for accurate great-circle distance between producer and customer
- Updated both marketplace/views.py and orders/views.py with expanded `POSTCODE_COORDS` dictionary
- System falls back to estimates (1 mile same outward, 15 miles same area, 60 miles different areas) for unlisted postcodes
- Food miles displayed on browse page and product detail page for logged-in customers
- Fixed stock quantity not updating after orders: corrected field name from 'stock' to 'stock_quantity'
- Stock now properly decrements when orders are completed through Stripe checkout
- Products automatically marked as unavailable when stock reaches 0
- Added stock validation to prevent orders when insufficient stock available
- Stock updates performed within database transaction to prevent race conditions