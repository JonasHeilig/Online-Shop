# Flask Online Shop with Stripe Payment Gateway

## Edit all Seacret Variabels to your own keys!


### Public Routes

- `/` - Home page of the application.
- `/register` - Registration page for new users.
- `/login` - Login page for users.
- `/products` - Product list displaying all available products.
- `/product/<int:id>` - Product view page for a specific product.

### Routes Requiring Login

- `/logout` - Logout page for users.
- `/transactions` - Page where users can view their transactions.
- `/thanks` - Thank you page displayed after a successful transaction.
- `/product/<int:id>/buy` - Purchase page for a specific product.

### Admin Routes

- `/product/add` - Page for adding products (admin only).
- `/product/list` - Page for listing products (admin only).
- `/product/<int:id>/edit` - Edit page for a specific product (admin only).