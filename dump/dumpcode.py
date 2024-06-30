@app.route('/', methods=['GET', 'POST'])
def index():
    product = stripe.Product.create(
        name='Test ProductV2',
        description='Your Product Description'
    )

    price = stripe.Price.create(
        product=product.id,
        unit_amount=1000,
        currency='eur',
    )

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': price.id,
            'quantity': 1,
        }],
        mode='payment',
        success_url=url_for('thanks', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=url_for('index', _external=True),
    )

    return render_template('index.html', stripe_public_key=app.config['STRIPE_PUBLIC_KEY'], checkout_public_key=session['id'])

