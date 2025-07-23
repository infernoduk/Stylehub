import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
# Import MySQL connector for database operations
import mysql.connector
# Import Error class for handling MySQL connection errors
from mysql.connector import Error
import random
import re
from mpesa_utils import initiate_stk_push

print('app.py is being loaded...')
app = Flask(__name__)
app.secret_key = '127575'  # set a secure secret key

# MySQL config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'flaskuser'
app.config['MYSQL_PASSWORD'] = 'newpassword'
app.config['MYSQL_DB'] = 'stylehub'

# M-Pesa config (replace with your actual credentials)
app.config['MPESA_CONSUMER_KEY'] = 'YOUR_CONSUMER_KEY'
app.config['MPESA_CONSUMER_SECRET'] = 'YOUR_CONSUMER_SECRET'
app.config['MPESA_BUSINESS_SHORTCODE'] = '174379'  # Example sandbox shortcode
app.config['MPESA_PASSKEY'] = 'YOUR_MPESA_PASSKEY'
app.config['MPESA_API_URL'] = 'https://sandbox.safaricom.co.ke' # Use 'https://api.safaricom.co.ke' for production

# File upload config
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Database setup
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB']
        )
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if conn is None:
        print("Failed to connect to database")
        return
    
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS `users` (
      `id` int NOT NULL AUTO_INCREMENT,
      `name` varchar(100) NOT NULL,
      `email` varchar(100) NOT NULL,
      `password` varchar(255) NOT NULL,
      `user_type` enum('buyer','seller','admin') NOT NULL,
      `mpesa_phone` varchar(15) DEFAULT NULL,
      `created_at` datetime NOT NULL,
      PRIMARY KEY (`id`),
      UNIQUE KEY `email` (`email`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS `products` (
      `id` int NOT NULL AUTO_INCREMENT,
      `title` varchar(255) NOT NULL,
      `description` text,
      `price` decimal(10,2) NOT NULL,
      `category` varchar(100) NOT NULL,
      `brand` varchar(100) DEFAULT NULL,
      `condition` varchar(50) NOT NULL,
      `location` varchar(100) DEFAULT NULL,
      `image` varchar(255) DEFAULT NULL,
      `seller_id` int NOT NULL,
      `created_at` datetime NOT NULL,
      PRIMARY KEY (`id`),
      KEY `seller_id` (`seller_id`),
      CONSTRAINT `products_ibfk_1` FOREIGN KEY (`seller_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS `orders` (
      `id` int NOT NULL AUTO_INCREMENT,
      `product_id` int NOT NULL,
      `buyer_id` int NOT NULL,
      `seller_id` int NOT NULL,
      `price` decimal(10,2) NOT NULL,
      `status` enum('pending_payment','paid_held_by_admin','completed','payment_failed','pending','paid') NOT NULL,
      `created_at` datetime NOT NULL,
      PRIMARY KEY (`id`),
      KEY `product_id` (`product_id`),
      KEY `buyer_id` (`buyer_id`),
      KEY `seller_id` (`seller_id`),
      CONSTRAINT `orders_ibfk_1` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE RESTRICT,
      CONSTRAINT `orders_ibfk_2` FOREIGN KEY (`buyer_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
      CONSTRAINT `orders_ibfk_3` FOREIGN KEY (`seller_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
    """)

    conn.commit()

    cursor.close()
    conn.close()
    print("Database tables created successfully")

# Helper functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_user(user_id):
    conn = get_db_connection()
    if conn is None:
        return None
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def get_product(product_id):
    conn = get_db_connection()
    if conn is None:
        return None
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return product

def get_products(filters=None, sort=None):
    conn = get_db_connection()
    if conn is None:
        return []
    
    cursor = conn.cursor(dictionary=True)
    query = 'SELECT * FROM products'
    params = []
    
    if filters:
        conditions = []
        if 'category' in filters and filters['category']:
            conditions.append('category = %s')
            params.append(filters['category'])
        if 'brand' in filters and filters['brand']:
            conditions.append('brand = %s')
            params.append(filters['brand'])
        if 'min_price' in filters and filters['min_price']:
            conditions.append('price >= %s')
            params.append(filters['min_price'])
        if 'max_price' in filters and filters['max_price']:
            conditions.append('price <= %s')
            params.append(filters['max_price'])
        if 'condition' in filters and filters['condition']:
            conditions.append('`condition` = %s')
            params.append(filters['condition'])
        if 'location' in filters and filters['location']:
            conditions.append('location = %s')
            params.append(filters['location'])
        
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
    
    if sort:
        if sort == 'price_low':
            query += ' ORDER BY price ASC'
        elif sort == 'price_high':
            query += ' ORDER BY price DESC'
        elif sort == 'newest':
            query += ' ORDER BY created_at DESC'
    else:
        query += ' ORDER BY created_at DESC'
    
    cursor.execute(query, params)
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return products

# Routes
@app.route('/')
def home():
    # Pagination
    page = int(request.args.get('page', 1))
    per_page = 6
    offset = (page - 1) * per_page
    
    conn = get_db_connection()
    if conn is None:
        return render_template('index.html', featured_products=[], categories=[], prev_page_url=None, next_page_url=None)
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM products ORDER BY RAND() LIMIT %s OFFSET %s', (per_page, offset))
    featured_products = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) as total FROM products')
    total_products = cursor.fetchone()['total']
    cursor.execute('SELECT DISTINCT category FROM products')
    categories = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Pagination URLs
    prev_page_url = url_for('home', page=page-1) if page > 1 else None
    next_page_url = url_for('home', page=page+1) if offset + per_page < total_products else None
    
    return render_template('index.html', 
                           featured_products=featured_products,
                           categories=categories,
                           prev_page_url=prev_page_url,
                           next_page_url=next_page_url)

@app.route('/products')
def product_listing():
    # Get filter parameters
    category = request.args.get('category')
    brand = request.args.get('brand')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    condition = request.args.get('condition')
    location = request.args.get('location')
    sort = request.args.get('sort')
    search_query = request.args.get('q')
    
    filters = {
        'category': category,
        'brand': brand,
        'min_price': min_price,
        'max_price': max_price,
        'condition': condition,
        'location': location
    }
    
    # Pagination
    page = int(request.args.get('page', 1))
    per_page = 6
    offset = (page - 1) * per_page
    
    # Get filtered and sorted products (all, for count)
    all_products = get_products(filters, sort)
    # Filter by search query if provided
    if search_query:
        sq = search_query.lower()
        all_products = [p for p in all_products if (
            sq in p['title'].lower() or
            sq in p['description'].lower() or
            sq in (p.get('category','') or '').lower() or
            sq in (p.get('brand','') or '').lower() or
            sq in (p.get('condition','') or '').lower() or
            sq in (p.get('location','') or '').lower()
        )]
    total_products = len(all_products)
    products = all_products[offset:offset+per_page]
    
    # Get filter options for the sidebar
    conn = get_db_connection()
    if conn is None:
        return render_template('products/listing.html', products=[], filters=filters, sort=sort,
                               categories=[], brands=[], conditions=[], locations=[], prev_page_url=None, next_page_url=None)
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT DISTINCT category FROM products')
    categories = cursor.fetchall()
    cursor.execute('SELECT DISTINCT brand FROM products')
    brands = cursor.fetchall()
    cursor.execute('SELECT DISTINCT `condition` FROM products')
    conditions = cursor.fetchall()
    cursor.execute('SELECT DISTINCT location FROM products')
    locations = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Pagination URLs
    prev_page_url = url_for('product_listing', page=page-1, **{k: v for k, v in filters.items() if v}) if page > 1 else None
    next_page_url = url_for('product_listing', page=page+1, **{k: v for k, v in filters.items() if v}) if offset + per_page < total_products else None
    
    return render_template('products/listing.html',
                           products=products,
                           filters=filters,
                           sort=sort,
                           categories=categories,
                           brands=brands,
                           conditions=conditions,
                           locations=locations,
                           prev_page_url=prev_page_url,
                           next_page_url=next_page_url)

@app.route('/products/<int:product_id>')
def product_detail(product_id):
    product = get_product(product_id)
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('product_listing'))
    
    seller = get_user(product['seller_id'])
    
    # Get related products (same category)
    conn = get_db_connection()
    if conn is None:
        related_products = []
    else:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT * FROM products WHERE category = %s AND id != %s LIMIT 4',
            (product['category'], product_id)
        )
        related_products = cursor.fetchall()
        cursor.close()
        conn.close()
    
    return render_template('products/detail.html',
                           product=product,
                           seller=seller,
                           related_products=related_products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        if conn is None:
            flash('Database connection error', 'error')
            return render_template('auth/login.html')
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            session['user_type'] = user['user_type']
            
            flash('Welcome back!', 'success')
            
            if user['user_type'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['user_type'] == 'seller':
                return redirect(url_for('seller_dashboard'))
            else:
                return redirect(url_for('buyer_dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        user_type = request.form['user_type']
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')
        
        conn = get_db_connection()
        if conn is None:
            flash('Database connection error', 'error')
            return render_template('auth/register.html')
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            cursor.close()
            conn.close()
            flash('Email already registered', 'error')
            return render_template('auth/register.html')
        
        hashed_password = generate_password_hash(password)
        
        cursor.execute(
            'INSERT INTO users (name, email, password, user_type, created_at) VALUES (%s, %s, %s, %s, %s)',
            (name, email, hashed_password, user_type, datetime.now())
        )
        conn.commit()
        
        # Get the newly created user
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        session.clear()
        session['user_id'] = user['id']
        session['user_type'] = user['user_type']
        
        flash('Registration successful!', 'success')
        
        if user_type == 'seller':
            return redirect(url_for('seller_dashboard'))
        else:
            return redirect(url_for('buyer_dashboard'))
    
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

# User dashboard routes
@app.route('/dashboard/buyer')
def buyer_dashboard():
    if 'user_id' not in session or session['user_type'] != 'buyer':
        flash('Please log in as a buyer', 'error')
        return redirect(url_for('login'))
    
    user = get_user(session['user_id'])
    
    conn = get_db_connection()
    if conn is None:
        orders = []
    else:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT orders.*, products.title, products.image FROM orders JOIN products ON orders.product_id = products.id WHERE orders.buyer_id = %s ORDER BY orders.created_at DESC',
            (session['user_id'],)
        )
        orders = cursor.fetchall()
        cursor.close()
        conn.close()
    
    return render_template('dashboard/buyer.html', user=user, orders=orders)

@app.route('/dashboard/seller')
def seller_dashboard():
    if 'user_id' not in session or session['user_type'] != 'seller':
        flash('Please log in as a seller', 'error')
        return redirect(url_for('login'))
    
    user = get_user(session['user_id'])
    
    conn = get_db_connection()
    if conn is None:
        products = []
        orders = []
    else:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT * FROM products WHERE seller_id = %s ORDER BY created_at DESC',
            (session['user_id'],)
        )
        products = cursor.fetchall()
        
        cursor.execute(
            'SELECT orders.*, products.title, users.name as buyer_name FROM orders JOIN products ON orders.product_id = products.id JOIN users ON orders.buyer_id = users.id WHERE products.seller_id = %s ORDER BY orders.created_at DESC',
            (session['user_id'],)
        )
        orders = cursor.fetchall()
        cursor.close()
        conn.close()
    
    return render_template('dashboard/seller.html', user=user, products=products, orders=orders)

@app.route('/dashboard/admin')
def admin_dashboard():
    if 'user_id' not in session or session['user_type'] != 'admin':
        flash('Please log in as an admin', 'error')
        return redirect(url_for('login'))
    
    user = get_user(session['user_id'])
    
    conn = get_db_connection()
    if conn is None:
        users = []
        products = []
        orders = []
    else:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        users = cursor.fetchall()
        cursor.execute('SELECT * FROM products ORDER BY created_at DESC')
        products = cursor.fetchall()
        cursor.execute(
            'SELECT orders.*, products.title, users.name as buyer_name FROM orders JOIN products ON orders.product_id = products.id JOIN users ON orders.buyer_id = users.id ORDER BY orders.created_at DESC'
        )
        orders = cursor.fetchall()
        cursor.close()
        conn.close()
    
    return render_template('admin/dashboard.html', user=user, users=users, products=products, orders=orders)

# Product management routes
@app.route('/products/create', methods=['GET', 'POST'])
def create_product():
    if 'user_id' not in session or session['user_type'] != 'seller':
        flash('Please log in as a seller', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = float(request.form['price'])
        category = request.form['category']
        brand = request.form['brand']
        condition = request.form['condition']
        location = request.form['location']
        
        # Handle image upload
        image = 'default.jpg'  # Default image
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to filename to avoid duplicates
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = filename
        
        conn = get_db_connection()
        if conn is not None:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO products (title, description, price, category, brand, `condition`, location, image, seller_id, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (title, description, price, category, brand, condition, location, image, session['user_id'], datetime.now())
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Product created successfully', 'success')
        else:
            flash('Database connection error', 'error')
        
        return redirect(url_for('seller_dashboard'))
    
    return render_template('products/create.html')

@app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    product = get_product(product_id)
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('seller_dashboard'))
    
    if 'user_id' not in session or (session['user_type'] != 'seller' and session['user_type'] != 'admin') or (session['user_type'] == 'seller' and product['seller_id'] != session['user_id']):
        flash('You do not have permission to edit this product', 'error')
        return redirect(url_for('product_detail', product_id=product_id))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = float(request.form['price'])
        category = request.form['category']
        brand = request.form['brand']
        condition = request.form['condition']
        location = request.form['location']
        
        # Handle image upload
        image = product['image']  # Keep existing image by default
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to filename to avoid duplicates
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = filename
        
        conn = get_db_connection()
        if conn is not None:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE products SET title = %s, description = %s, price = %s, category = %s, brand = %s, `condition` = %s, location = %s, image = %s WHERE id = %s',
                (title, description, price, category, brand, condition, location, image, product_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Product updated successfully', 'success')
        else:
            flash('Database connection error', 'error')
        
        return redirect(url_for('product_detail', product_id=product_id))
    
    return render_template('products/edit.html', product=product)

@app.route('/products/<int:product_id>/delete', methods=['POST'])
def delete_product(product_id):
    product = get_product(product_id)
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('seller_dashboard'))
    
    if 'user_id' not in session or (session['user_type'] != 'seller' and session['user_type'] != 'admin') or (session['user_type'] == 'seller' and product['seller_id'] != session['user_id']):
        flash('You do not have permission to delete this product', 'error')
        return redirect(url_for('product_detail', product_id=product_id))
    
    conn = get_db_connection()
    if conn is not None:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE id = %s', (product_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Product deleted successfully', 'success')
    else:
        flash('Database connection error', 'error')
    
    if session['user_type'] == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('seller_dashboard'))

# Order management
@app.route('/products/<int:product_id>/buy', methods=['POST'])
def buy_product(product_id):
    if 'user_id' not in session or session['user_type'] != 'buyer':
        flash('Please log in as a buyer', 'error')
        return redirect(url_for('login'))
    
    product = get_product(product_id)
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('product_listing'))
    
    quantity = int(request.form.get('quantity', 1))
    total_price = product['price'] * quantity
    
    conn = get_db_connection()
    if conn is not None:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO orders (product_id, buyer_id, seller_id, price, status, created_at) VALUES (%s, %s, %s, %s, %s, %s)',
            (product_id, session['user_id'], product['seller_id'], total_price, 'pending', datetime.now())
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Order placed successfully', 'success')
    else:
        flash('Database connection error', 'error')
    
    return redirect(url_for('buyer_dashboard'))

@app.route('/orders/<int:order_id>/update', methods=['POST'])
def update_order_status(order_id):
    if 'user_id' not in session or session['user_type'] != 'seller':
        flash('Please log in as a seller', 'error')
        return redirect(url_for('login'))
    
    status = request.form['status']
    
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error', 'error')
        return redirect(url_for('seller_dashboard'))
    
    cursor = conn.cursor(dictionary=True)
    # Verify the seller owns the product in this order
    cursor.execute(
        'SELECT orders.*, products.seller_id FROM orders JOIN products ON orders.product_id = products.id WHERE orders.id = %s',
        (order_id,)
    )
    order = cursor.fetchone()
    
    if not order or order['seller_id'] != session['user_id']:
        cursor.close()
        conn.close()
        flash('You do not have permission to update this order', 'error')
        return redirect(url_for('seller_dashboard'))
    
    cursor.execute('UPDATE orders SET status = %s WHERE id = %s', (status, order_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Order status updated successfully', 'success')
    return redirect(url_for('seller_dashboard'))

# User profile management
@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('Please log in', 'error')
        return redirect(url_for('login'))
    
    user = get_user(session['user_id'])
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        
        conn = get_db_connection()
        if conn is None:
            flash('Database connection error', 'error')
            return render_template('dashboard/edit_profile.html', user=user)
        
        cursor = conn.cursor(dictionary=True)
        # Check if email is already taken by another user
        cursor.execute('SELECT * FROM users WHERE email = %s AND id != %s', (email, session['user_id']))
        existing_user = cursor.fetchone()
        
        if existing_user:
            cursor.close()
            conn.close()
            flash('Email already taken', 'error')
            return render_template('dashboard/edit_profile.html', user=user)
        
        cursor.execute('UPDATE users SET name = %s, email = %s WHERE id = %s', (name, email, session['user_id']))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Profile updated successfully', 'success')
        
        if session['user_type'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session['user_type'] == 'seller':
            return redirect(url_for('seller_dashboard'))
        else:
            return redirect(url_for('buyer_dashboard'))
    
    return render_template('dashboard/edit_profile.html', user=user)

# Admin user management
@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or session['user_type'] != 'admin':
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('home'))
    
    if user_id == session['user_id']:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin_dashboard'))
    
    conn = get_db_connection()
    if conn is not None:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('User deleted successfully', 'success')
    else:
        flash('Database connection error', 'error')
    
    return redirect(url_for('admin_dashboard'))

# --- CART ROUTES ---
@app.route('/cart')
def view_cart():
    if 'user_id' not in session or session.get('user_type') != 'buyer':
        flash('Please log in as a buyer to view your cart.', 'error')
        return redirect(url_for('login'))
    cart = session.get('cart', {})
    cart_items = []
    total = 0
    for product_id, item in cart.items():
        product = get_product(product_id)
        if product:
            quantity = item['quantity']
            subtotal = product['price'] * quantity
            total += subtotal
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })
    return render_template('cart/cart.html', cart_items=cart_items, total=total)

@app.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session or session.get('user_type') != 'buyer':
        flash('Please log in as a buyer to add items to your cart.', 'error')
        return redirect(url_for('login'))
    quantity = int(request.form.get('quantity', 1))
    cart = session.get('cart', {})
    product_id_str = str(product_id)
    if product_id_str in cart:
        cart[product_id_str]['quantity'] += quantity
    else:
        cart[product_id_str] = {'quantity': quantity}
    session['cart'] = cart
    flash('Product added to cart!', 'success')
    return redirect(request.referrer or url_for('product_listing'))

@app.route('/cart/update/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    if 'user_id' not in session or session.get('user_type') != 'buyer':
        flash('Please log in as a buyer to update your cart.', 'error')
        return redirect(url_for('login'))
    quantity = int(request.form.get('quantity', 1))
    cart = session.get('cart', {})
    product_id_str = str(product_id)
    if product_id_str in cart:
        if quantity > 0:
            cart[product_id_str]['quantity'] = quantity
        else:
            del cart[product_id_str]
        session['cart'] = cart
    return redirect(url_for('view_cart'))

@app.route('/cart/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if 'user_id' not in session or session.get('user_type') != 'buyer':
        flash('Please log in as a buyer to update your cart.', 'error')
        return redirect(url_for('login'))
    cart = session.get('cart', {})
    product_id_str = str(product_id)
    if product_id_str in cart:
        del cart[product_id_str]
        session['cart'] = cart
    return redirect(url_for('view_cart'))

# --- CHECKOUT ROUTE ---
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session or session.get('user_type') != 'buyer':
        flash('Please log in as a buyer to checkout.', 'error')
        return redirect(url_for('login'))
    cart = session.get('cart', {})
    cart_items = []
    total = 0
    for product_id, item in cart.items():
        product = get_product(product_id)
        if product:
            quantity = item['quantity']
            subtotal = product['price'] * quantity
            total += subtotal
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })
    if request.method == 'POST':
        phone_number = request.form.get('phone')
        if not phone_number or not re.match(r'^(07|01)\d{8}$', phone_number):
             flash('Please enter a valid M-Pesa phone number (e.g. 0712345678).', 'error')
             return render_template('cart/checkout.html', cart_items=cart_items, total=total)
        
        # Create a single order for the total amount
        conn = get_db_connection()
        if conn is not None:
            cursor = conn.cursor()
            
            # Create a 'pending' order to get an ID
            # In a real app, you might create a single order record with a summary
            # For simplicity, we'll just use the total and link to the first product
            first_product_id = cart_items[0]['product']['id'] if cart_items else None
            seller_id = cart_items[0]['product']['seller_id'] if cart_items else None

            if first_product_id:
                cursor.execute(
                    'INSERT INTO orders (product_id, buyer_id, seller_id, price, status, created_at) VALUES (%s, %s, %s, %s, %s, %s)',
                    (first_product_id, session['user_id'], seller_id, total, 'pending_payment', datetime.now())
                )
                conn.commit()
                order_id = cursor.lastrowid
                
                # Initiate STK Push
                mpesa_response = initiate_stk_push(phone_number, int(total), order_id)

                if mpesa_response and mpesa_response.get('ResponseCode') == '0':
                    session['cart'] = {}  # Clear cart
                    flash('Please check your phone to complete the M-Pesa payment.', 'info')
                    return redirect(url_for('buyer_dashboard'))
                else:
                    flash('Failed to initiate M-Pesa payment. Please try again.', 'error')
                    # Optional: Delete the pending order if STK push fails
                    cursor.execute('DELETE FROM orders WHERE id = %s', (order_id,))
                    conn.commit()
            
            cursor.close()
            conn.close()
        else:
            flash('Database connection error', 'error')

        return render_template('cart/checkout.html', cart_items=cart_items, total=total)

    return render_template('cart/checkout.html', cart_items=cart_items, total=total)


@app.route('/mpesa/callback/<int:order_id>', methods=['POST'])
def mpesa_callback(order_id):
    """Handle M-Pesa STK Push callback."""
    callback_data = request.get_json()
    
    # {
    #   "Body": {
    #     "stkCallback": {
    #       "MerchantRequestID": "...",
    #       "CheckoutRequestID": "...",
    #       "ResultCode": 0,
    #       "ResultDesc": "The service request is processed successfully.",
    #       "CallbackMetadata": { ... }
    #     }
    #   }
    # }

    if callback_data.get('Body', {}).get('stkCallback', {}).get('ResultCode') == 0:
        # Payment was successful
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE orders SET status = %s WHERE id = %s', ('paid_held_by_admin', order_id))
            conn.commit()
            cursor.close()
            conn.close()
    else:
        # Payment failed or was canceled
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE orders SET status = %s WHERE id = %s', ('payment_failed', order_id))
            conn.commit()
            cursor.close()
            conn.close()
            
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

# Initialize the database if it doesn't exist
@app.cli.command('init-db')
def init_db_command():
    init_db()
    print('Initialized the database.')

# Add sample data for testing
@app.cli.command('seed-db')
def seed_db_command():
    print('Starting seed_db_command...')
    try:
        conn = get_db_connection()
        if conn is None:
            print("Failed to connect to database")
            return
        
        cursor = conn.cursor(dictionary=True)
        print('Connected to database.')
        # Add admin user
        admin_password = generate_password_hash('admin123')
        cursor.execute(
            'INSERT INTO users (name, email, password, user_type, created_at) VALUES (%s, %s, %s, %s, %s)',
            ('Admin User', 'admin@stylehub.com', admin_password, 'admin', datetime.now())
        )
        print('Admin user added.')
        # Add seller user
        seller_password = generate_password_hash('seller123')
        cursor.execute(
            'INSERT INTO users (name, email, password, user_type, created_at) VALUES (%s, %s, %s, %s, %s)',
            ('Seller User', 'seller@stylehub.com', seller_password, 'seller', datetime.now())
        )
        print('Seller user added.')
        # Add buyer user
        buyer_password = generate_password_hash('buyer123')
        cursor.execute(
            'INSERT INTO users (name, email, password, user_type, created_at) VALUES (%s, %s, %s, %s, %s)',
            ('Buyer User', 'buyer@stylehub.com', buyer_password, 'buyer', datetime.now())
        )
        print('Buyer user added.')
        # Add sample products
        categories = ['Clothing', 'Shoes', 'Accessories', 'Bags', 'Jewelry']
        brands = ['Nike', 'Adidas', 'Zara', 'H&M', 'Gucci', 'Prada']
        conditions = ['New', 'Used - Like New', 'Used - Good', 'Used - Fair']
        locations = ['New York', 'Los Angeles', 'Chicago', 'Miami', 'Dallas']
        cursor.execute('SELECT id FROM users WHERE email = %s', ('seller@stylehub.com',))
        seller_row = cursor.fetchone()
        if not seller_row:
            print("Could not find seller user to seed products.")
            cursor.close()
            conn.close()
            return
        seller_id = seller_row['id']
        print('Seller ID:', seller_id)
        unsplash_images = [
            'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?auto=format&fit=crop&w=400&q=80',
            'https://images.unsplash.com/photo-1469398715555-76331a6c7c9b?auto=format&fit=crop&w=400&q=80',
            'https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=400&q=80',
            'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=400&q=80',
            'https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?auto=format&fit=crop&w=400&q=80',
            'https://images.unsplash.com/photo-1465101046530-73398c7f28ca?auto=format&fit=crop&w=400&q=80',
            'https://images.unsplash.com/photo-1511367461989-f85a21fda167?auto=format&fit=crop&w=400&q=80',
            'https://images.unsplash.com/photo-1465101178521-c1a9136a3b99?auto=format&fit=crop&w=400&q=80',
            'https://images.unsplash.com/photo-1519125323398-675f0ddb6308?auto=format&fit=crop&w=400&q=80',
            'https://images.unsplash.com/photo-1515378791036-0648a3ef77b2?auto=format&fit=crop&w=400&q=80'
        ]
        for i in range(20):
            title = f"Product {i+1}"
            description = f"This is a description for product {i+1}. It's a great product with many features."
            price = round(random.uniform(10.0, 500.0), 2)
            category = random.choice(categories)
            brand = random.choice(brands)
            condition = random.choice(conditions)
            location = random.choice(locations)
            image = unsplash_images[i % len(unsplash_images)]
            cursor.execute(
                'INSERT INTO products (title, description, price, category, brand, `condition`, location, image, seller_id, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (title, description, price, category, brand, condition, location, image, seller_id, datetime.now())
            )
            print(f'Added product {i+1} with image: {image}')
        conn.commit()
        cursor.close()
        conn.close()
        print('Added sample data to the database.')
    except Exception as e:
        print('Error during seed_db_command:', e)

if __name__ == '__main__':
    app.run(debug=True)
