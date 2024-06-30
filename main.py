#  Import Secrets
from secret import stripe_public_key, stripe_secret_key
#  Import Other Libraries
from flask import Flask, render_template, request, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
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
    prices = db.relationship('ProductPrice', back_populates='product', lazy=True)


class ProductPrice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    stripe_price_id = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    active = db.Column(db.Boolean, default=False)

    product = db.relationship('Product', back_populates='prices')


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(128))
    isAdmin = db.Column(db.Boolean, default=False)
    stripe_customer_id = db.Column(db.String(100), nullable=True)


if not os.path.exists('instance/db.db'):
    with app.app_context():
        db.create_all()
        print("Datenbank erstellt.")


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


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
            return render_template('login.html', app_name=app_name, error="Invalid username or password")
    return render_template('login.html', app_name=app_name, error=error)


@app.route('/thanks')
def thanks():
    payment_session_id = request.args.get('payment_session_id')
    if payment_session_id:
        try:
            session = stripe.checkout.Session.retrieve(payment_session_id)
            payment_intent_id = session.payment_intent
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            transaction_id = payment_intent.id
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
    products = Product.query.all()
    return render_template('products.html', products=products)


@app.route('/product/add', methods=['GET', 'POST'])
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


@app.route('/product/<int:id>')
def view_product(id):
    product = Product.query.get_or_404(id)
    active_price = ProductPrice.query.filter_by(product_id=id, active=True).first()
    return render_template('view_product.html', product=product, active_price=active_price)


@app.route('/product/<int:id>/edit', methods=['GET', 'POST'])
def edit_product(id):
    product = Product.query.get_or_404(id)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'edit_product':
            product.name = request.form.get('name')
            product.description = request.form.get('description')

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


if __name__ == '__main__':
    app.run(debug=True, port=5550)
