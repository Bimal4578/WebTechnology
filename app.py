import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Product, CartItem, Order, OrderItem

# Initialize the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here_override_in_production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---

@app.before_request
def setup_database():
    # Only run this once
    if getattr(app, '_database_initialized', False):
        return
        
    db.create_all()
    # Create an admin user if missing
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('adminpass')
        db.session.add(admin)
    
    # Add dummy products if missing
    if Product.query.count() == 0:
        products = [
            Product(name="Classic T-Shirt", description="A comfortable cotton t-shirt.", price=19.99, category="T-Shirts", stock=100, image_url="https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60"),
            Product(name="Denim Jeans", description="Durable blue jeans.", price=49.99, category="Pants", stock=50, image_url="https://images.unsplash.com/photo-1542272604-780c8d10333d?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60"),
            Product(name="Leather Jacket", description="Stylish leather jacket.", price=129.99, category="Jackets", stock=20, image_url="https://images.unsplash.com/photo-1551028719-00167b16eac5?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60"),
            Product(name="Summer Dress", description="Light and breezy dress.", price=39.99, category="Dresses", stock=30, image_url="https://images.unsplash.com/photo-1515347619152-16782eb06a6c?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60"),
            Product(name="Running Shoes", description="Comfortable sneakers.", price=79.99, category="Shoes", stock=40, image_url="https://images.unsplash.com/photo-1542291026-7eec264c27ff?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60"),
            Product(name="Winter Scarf", description="Warm wool scarf.", price=24.99, category="Accessories", stock=60, image_url="https://images.unsplash.com/photo-1606760227091-3dd870d97f1d?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60")
        ]
        db.session.bulk_save_objects(products)
        
    db.session.commit()
    app._database_initialized = True

@app.route('/')
def index():
    featured_products = Product.query.limit(4).all()
    return render_template('index.html', products=featured_products)

@app.route('/shop')
def shop():
    category = request.args.get('category')
    if category:
        products = Product.query.filter_by(category=category).all()
    else:
        products = Product.query.all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template('shop.html', products=products, categories=categories, current_category=category)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)

# --- Authentication Routes ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not email or not password:
            flash('Please fill out all fields.', 'danger')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        user_exists = User.query.filter_by(username=username).first()
        email_exists = User.query.filter_by(email=email).first()

        if user_exists:
            flash('Username is already taken.', 'danger')
            return redirect(url_for('register'))
        if email_exists:
            flash('Email is already registered.', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('login'))

        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# --- Cart and Checkout Routes ---

@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))

    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product.id, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    flash(f'Added {product.name} to your cart.', 'success')
    return redirect(request.referrer or url_for('shop'))

@app.route('/update-cart/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('cart'))
        
    action = request.form.get('action')
    if action == 'increment':
        cart_item.quantity += 1
    elif action == 'decrement' and cart_item.quantity > 1:
        cart_item.quantity -= 1
    elif action == 'remove':
        db.session.delete(cart_item)
        
    db.session.commit()
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('shop'))
        
    total = sum(item.product.price * item.quantity for item in cart_items)

    if request.method == 'POST':
        # Create order
        order = Order(user_id=current_user.id, total_price=total)
        db.session.add(order)
        db.session.commit() # Commit to get order.id
        
        # Add order items and clear cart
        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id, 
                product_id=item.product_id, 
                quantity=item.quantity, 
                price=item.product.price
            )
            db.session.add(order_item)
            db.session.delete(item)
            
        db.session.commit()
        flash('Order placed successfully!', 'success')
        return redirect(url_for('index'))
        
    return render_template('checkout.html', cart_items=cart_items, total=total)

# --- Admin Routes ---

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Administrator privileges required.', 'danger')
        return redirect(url_for('index'))
    products = Product.query.all()
    users = User.query.all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/dashboard.html', products=products, users=users, orders=orders)

@app.route('/admin/product/add', methods=['GET', 'POST'])
@login_required
def admin_add_product():
    if not current_user.is_admin:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        category = request.form.get('category')
        image_url = request.form.get('image_url') or 'default.jpg'
        stock = int(request.form.get('stock', 0))
        
        new_product = Product(name=name, description=description, price=price, category=category, image_url=image_url, stock=stock)
        db.session.add(new_product)
        db.session.commit()
        
        flash('Product added successfully.', 'success')
        return redirect(url_for('admin_dashboard'))
        
    return render_template('admin/add_product.html')

@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_product(product_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
        
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.price = float(request.form.get('price'))
        product.category = request.form.get('category')
        product.image_url = request.form.get('image_url') or 'default.jpg'
        product.stock = int(request.form.get('stock', 0))
        
        db.session.commit()
        flash('Product updated successfully.', 'success')
        return redirect(url_for('admin_dashboard'))
        
    return render_template('admin/edit_product.html', product=product)

@app.route('/admin/product/delete/<int:product_id>', methods=['POST'])
@login_required
def admin_delete_product(product_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
        
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))


# --- CLI Commands for setting up ---
@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("Database initialized.")
    # Create an admin user
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('adminpass')
        db.session.add(admin)
        print("Admin user created (admin / adminpass).")
    
    # Add dummy products
    if Product.query.count() == 0:
        products = [
            Product(name="Classic T-Shirt", description="A comfortable cotton t-shirt.", price=19.99, category="T-Shirts", stock=100, image_url="https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60"),
            Product(name="Denim Jeans", description="Durable blue jeans.", price=49.99, category="Pants", stock=50, image_url="https://images.unsplash.com/photo-1542272604-780c8d10333d?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60"),
            Product(name="Leather Jacket", description="Stylish leather jacket.", price=129.99, category="Jackets", stock=20, image_url="https://images.unsplash.com/photo-1551028719-00167b16eac5?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60"),
            Product(name="Summer Dress", description="Light and breezy dress.", price=39.99, category="Dresses", stock=30, image_url="https://images.unsplash.com/photo-1515347619152-16782eb06a6c?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60"),
            Product(name="Running Shoes", description="Comfortable sneakers.", price=79.99, category="Shoes", stock=40, image_url="https://images.unsplash.com/photo-1542291026-7eec264c27ff?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60"),
            Product(name="Winter Scarf", description="Warm wool scarf.", price=24.99, category="Accessories", stock=60, image_url="https://images.unsplash.com/photo-1606760227091-3dd870d97f1d?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60")
        ]
        db.session.bulk_save_objects(products)
        print("Sample products added.")
        
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        # Ensure database is created on startup if we don't have it
        if not os.path.exists('store.db'):
            db.create_all()
    app.run(debug=True, port=5000)
