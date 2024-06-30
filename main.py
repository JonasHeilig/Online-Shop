#  Import Secrets
from secret import stripe_public_key, stripe_secret_key
#  Import Other Libraries
from flask import Flask, render_template, request, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
import stripe

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['STRIPE_PUBLIC_KEY'] = stripe_public_key
app.config['STRIPE_SECRET_KEY'] = stripe_secret_key
app.secret_key = 'secret_salt'  # Change this on Public build!
db = SQLAlchemy(app)

stripe.api_key = app.config['STRIPE_SECRET_KEY']


@app.route('/', methods=['GET', 'POST'])
def index():
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': 'price_1PXIJuEBNfzifYAVgKFjthuA',
            'quantity': 1,
        }],
        mode='payment',
        success_url=url_for('thanks', _external=True) + '?session_id={CHECKOUT_SESSION_ID}?transaction_id={CHECKOUT_SESSION_ID}',
        cancel_url=url_for('index', _external=True),
    )
    return render_template('index.html', stripe_public_key=app.config['STRIPE_PUBLIC_KEY'],
                           checkout_public_key=session['id'])


@app.route('/thanks')
def thanks():
    session_id = request.args.get('session_id')
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            payment_intent_id = session.payment_intent
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            transaction_id = payment_intent.id
        except stripe.error.InvalidRequestError:
            transaction_id = 'Invalid session ID'

    return render_template('thanks.html', transaction_id=transaction_id, session_id=session_id)


if __name__ == '__main__':
    app.run(debug=True, port=5550)
