#  Import Secrets
from secret import stripe_public_key, stripe_secret_key
#  Import Other Libraries
from flask import Flask, render_template, request, redirect, url_for, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import stripe
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['STRIPE_PUBLIC_KEY'] = stripe_public_key
app.config['STRIPE_SECRET_KEY'] = stripe_secret_key
app.secret_key = 'secret_salt'  # Change this on Public build!
db = SQLAlchemy(app)

stripe.api_key = app.config['STRIPE_SECRET_KEY']


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    stripe_product_id = db.Column(db.String(100), nullable=False)
    is_purchasable = db.Column(db.Boolean, default=True)
    prices = db.relationship('ProductPrice', back_populates='product', lazy=True)


class ProductPrice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    stripe_price_id = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    active = db.Column(db.Boolean, default=False)

    product = db.relationship('Product', back_populates='prices')


class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    transaction_id = db.Column(db.String(100), nullable=True)
    payment_session_id = db.Column(db.String(100), nullable=True)

    user = db.relationship('User', back_populates='purchases')
    product = db.relationship('Product')


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(128))
    isAdmin = db.Column(db.Boolean, default=False)
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    purchases = db.relationship('Purchase', back_populates='user', lazy=True)


if not os.path.exists('instance/db.db'):
    with app.app_context():
        db.create_all()
        print("Datenbank erstellt.")


def check_permissions(required_permissions):
    if 'username' not in session:
        return False
    session_user = db.session.get(User, session['user_id'])
    for permission in required_permissions:
        if not getattr(session_user, permission):
            return False
    return True


def requires_permission(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not check_permissions([permission]):
                return redirect(url_for('login'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = request.args.get('error', '')
    if 'username' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        session_user = User.query.filter_by(username=username).first()
        if session_user and check_password_hash(session_user.password, password):
            session['username'] = username
            session['user_id'] = session_user.id
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid username or password")
    return render_template('login.html', error=error)


@app.route('/transactions', methods=['GET'])
def transactions():
    if 'username' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    purchases = Purchase.query.filter_by(user_id=user_id).all()
    return render_template('transactions.html', purchases=purchases)


@app.route('/thanks')
def thanks():
    transaction_id = None
    payment_session_id = request.args.get('payment_session_id')
    if payment_session_id:
        try:
            session = stripe.checkout.Session.retrieve(payment_session_id)
            payment_intent_id = session.payment_intent
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            transaction_id = payment_intent.id

            purchase = Purchase.query.filter_by(user_id=session['user_id']).first()
            if purchase:
                purchase.transaction_id = transaction_id
                purchase.payment_session_id = payment_session_id
                db.session.commit()

        except stripe.error.InvalidRequestError:
            transaction_id = 'Invalid session ID'

    return render_template('thanks.html', transaction_id=transaction_id, payment_session_id=payment_session_id)


@app.route('/product')
def product():
    return redirect('/products')


@app.route('/product/')
def product_second():
    return redirect('/products')


@app.route('/products', methods=['GET'])
def products():
    products = Product.query.filter_by(is_purchasable=True).all()
    return render_template('products.html', products=products)


@app.route('/product/add', methods=['GET', 'POST'])
@requires_permission('isAdmin')
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = int(request.form.get('price'))

        stripe_product = stripe.Product.create(name=name, description=description)
        stripe_price = stripe.Price.create(product=stripe_product.id, unit_amount=price, currency='eur')

        product = Product(name=name, description=description, stripe_product_id=stripe_product.id)
        db.session.add(product)
        db.session.commit()

        product_price = ProductPrice(product_id=product.id, stripe_price_id=stripe_price.id, price=price, active=True)
        db.session.add(product_price)
        db.session.commit()

        return redirect(url_for('view_product', id=product.id))

    return render_template('add_product.html')


@app.route('/product/list', methods=['GET', 'POST'])
@requires_permission('isAdmin')
def list_products():
    products = Product.query.all()

    if request.method == 'POST':
        product_id = request.form.get('product_id')
        product = Product.query.get(product_id)

        if product:
            product.name = request.form.get('name')
            product.description = request.form.get('description')
            product.is_purchasable = 'is_purchasable' in request.form

            stripe.Product.modify(product.stripe_product_id, name=product.name, description=product.description)

            db.session.commit()

    return render_template('list_products.html', products=products)


@app.route('/product/<int:id>')
def view_product(id):
    product = Product.query.get_or_404(id)
    active_price = ProductPrice.query.filter_by(product_id=id, active=True).first()
    return render_template('view_product.html', product=product, active_price=active_price,
                           stripe_public_key=app.config['STRIPE_PUBLIC_KEY'])


@app.route('/product/<int:id>/buy', methods=['POST'])
def buy_product(id):
    product = Product.query.get_or_404(id)
    active_price = ProductPrice.query.filter_by(product_id=id, active=True).first()

    if not active_price:
        return "No active price for this product", 400

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': active_price.stripe_price_id,
            'quantity': 1,
        }],
        mode='payment',
        success_url=url_for('thanks', _external=True) + '?payment_session_id={CHECKOUT_SESSION_ID}',
        cancel_url=url_for('view_product', id=id, _external=True),
    )

    return jsonify({'id': session.id})


@app.route('/product/<int:id>/edit', methods=['GET', 'POST'])
@requires_permission('isAdmin')
def edit_product(id):
    product = Product.query.get_or_404(id)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'edit_product':
            product.name = request.form.get('name')
            product.description = request.form.get('description')
            product.is_purchasable = 'is_purchasable' in request.form

            stripe.Product.modify(product.stripe_product_id, name=product.name, description=product.description)

            db.session.commit()

            return redirect(url_for('view_product', id=product.id))

        elif action == 'add_price':
            price = int(request.form.get('price'))
            stripe_price = stripe.Price.create(product=product.stripe_product_id, unit_amount=price, currency='eur')

            product_price = ProductPrice(product_id=id, stripe_price_id=stripe_price.id, price=price)
            db.session.add(product_price)
            db.session.commit()

            return redirect(url_for('edit_product', id=product.id))

        elif action == 'set_price':
            price_id = int(request.form.get('price_id'))
            for price in product.prices:
                price.active = (price.id == price_id)
            db.session.commit()

            return redirect(url_for('edit_product', id=product.id))

    return render_template('edit_product.html', product=product)


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=5550)
