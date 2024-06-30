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
    price = db.Column(db.Integer, nullable=False)  # Price in cents
    stripe_product_id = db.Column(db.String(100), nullable=False)
    stripe_price_id = db.Column(db.String(100), nullable=False)


if not os.path.exists('instance/db.db'):
    with app.app_context():
        db.create_all()
        print("Datenbank erstellt.")


@app.route('/', methods=['GET', 'POST'])
def index():
    payment_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': 'price_1PXIJuEBNfzifYAVgKFjthuA',
            'quantity': 1,
        }],
        mode='payment',
        success_url=url_for('thanks',
                            _external=True) + '?payment_session_id={CHECKOUT_SESSION_ID}?transaction_id={CHECKOUT_SESSION_ID}',
        cancel_url=url_for('index', _external=True),
    )
    return render_template('index.html', stripe_public_key=app.config['STRIPE_PUBLIC_KEY'],
                           checkout_public_key=payment_session['id'])


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


@app.route('/product/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = int(request.form.get('price'))

        stripe_product = stripe.Product.create(name=name, description=description)
        stripe_price = stripe.Price.create(product=stripe_product.id, unit_amount=price, currency='eur')

        product = Product(name=name, description=description, price=price,
                          stripe_product_id=stripe_product.id, stripe_price_id=stripe_price.id)
        db.session.add(product)
        db.session.commit()

        return redirect(url_for('view_product', id=product.id))

    return render_template('add_product.html')


@app.route('/product/<int:id>')
def view_product(id):
    product = Product.query.get_or_404(id)
    return render_template('view_product.html', product=product)


if __name__ == '__main__':
    app.run(debug=True, port=5550)
