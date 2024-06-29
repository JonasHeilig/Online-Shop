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


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/thanks/<transaction_id>')
def thanks(transaction_id):
    additional_info = None
    return render_template('thanks.html', transaction_id=transaction_id, additional_info=additional_info)


if __name__ == '__main__':
    app.run(debug=True, port=5550)
