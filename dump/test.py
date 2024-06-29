import stripe
from secret import stripe_secret_key


stripe.api_key = stripe_secret_key


payment_intent = stripe.PaymentIntent.create(
  amount=1000,
  currency='usd',
  payment_method_types=['card'],
)

print(f"Created PaymentIntent: {payment_intent.id}")


confirmed_payment_intent = stripe.PaymentIntent.confirm(payment_intent.id)

print(f"Confirmed PaymentIntent: {confirmed_payment_intent.id}, Status: {confirmed_payment_intent.status}")