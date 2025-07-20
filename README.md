# StyleHub - Fashion E-commerce Platform

## Overview
StyleHub is a comprehensive e-commerce platform designed for fashion products. It connects buyers with sellers in a user-friendly marketplace, allowing users to browse, buy, and sell clothing, shoes, accessories, and more.

## Features

### User Management
- **Multiple User Types**: Support for buyers, sellers, and administrators
- **Authentication**: Secure login and registration system
- **Profile Management**: Users can edit their profile information

### Product Management
- **Product Listings**: Sellers can create, edit, and delete product listings
- **Product Details**: Comprehensive product information including title, description, price, category, brand, condition, and location
- **Image Upload**: Support for product images

### Shopping Experience
- **Product Search**: Filter products by category, brand, price range, condition, and location
- **Product Sorting**: Sort products by price (low to high, high to low) or newest first
- **Related Products**: View related products in the same category

### Order Management
- **Purchase System**: Buyers can place orders for products
- **Order Tracking**: Buyers can view their order history
- **Order Status Updates**: Sellers can update the status of orders (pending, confirmed, shipped, delivered, cancelled)

### Admin Dashboard
- **User Management**: View and delete users
- **Product Oversight**: View all products in the system
- **Order Monitoring**: Track all orders in the system

## Technology Stack

### Backend
- **Flask**: Python web framework
- **MySQL**: Database for storing user, product, and order information
- **Werkzeug**: For password hashing and file uploads

### Frontend
- **HTML/CSS/JavaScript**: Frontend development
- **Bootstrap**: Responsive design framework
- **Jinja2**: Template engine for Python
- **Font Awesome**: Icon library

## Installation

### Prerequisites
- Python 3.6 or higher
- MySQL

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/stylehub.git
   cd stylehub
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Configure MySQL:
   - Create a MySQL database named `stylehub`
   - Create a MySQL user `flaskuser` with password `newpassword`
   - Grant all privileges on the `stylehub` database to `flaskuser`

5. Initialize the database:
   ```
   flask init-db
   ```

6. (Optional) Add sample data:
   ```
   flask seed-db
   ```

7. Run the application:
   ```
   flask run
   ```
   or
   ```
   python app.py
   ```

8. Access the application at `http://127.0.0.1:5000`

## Usage

### Default Accounts (if using sample data)
- **Admin**: admin@stylehub.com / admin123
- **Seller**: seller@stylehub.com / seller123
- **Buyer**: admin@stylehub.com / buyer123

### Buyer Guide
1. Register as a buyer or log in with the sample buyer account
2. Browse products by category or use the search/filter options
3. View product details and related products
4. Add products to cart and complete the purchase
5. Track orders in the buyer dashboard

### Seller Guide
1. Register as a seller or log in with the sample seller account
2. Create product listings with detailed information and images
3. Manage product listings (edit or delete)
4. Process orders by updating their status
5. Track sales in the seller dashboard

### Admin Guide
1. Log in with the admin account
2. Manage users (view or delete)
3. Monitor all products in the system
4. Track all orders in the system

## Project Structure

```
stylehub/
├── app.py                  # Main application file
├── schema.sql              # Database schema
├── static/                 # Static files
│   ├── css/                # CSS files
│   ├── js/                 # JavaScript files
│   └── uploads/            # Uploaded product images
└── templates/              # HTML templates
    ├── admin/              # Admin templates
    ├── auth/               # Authentication templates
    ├── dashboard/          # User dashboard templates
    ├── products/           # Product templates
    ├── base.html           # Base template
    └── index.html          # Home page template
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Flask team for the excellent web framework
- Bootstrap team for the responsive design framework
- Font Awesome for the icon library