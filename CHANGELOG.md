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