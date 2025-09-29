import stripe
from yookassa import Payment, Webhook
from django.conf import settings
from django.shortcuts import redirect, get_object_or_404, render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from orders.models import Order
from cart.cart import Cart
from decimal import Decimal
import json
import logging

logger = logging.getLogger(__name__)

# Stripe settings
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe_endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

# Yookassa settings
from yookassa import Configuration
Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


def create_stripe_checkout_session(order, request):
    cart = Cart(request)
    line_items = []
    for item in cart:
        if item['type'] == 'product':
            line_items.append({
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': f"{item['perfume'].name} - {item['capacity'].volume}",
                    },
                    'unit_amount': int(item['price'] * 100),
                },
                'quantity': item['quantity'],
            })
        elif item['type'] == 'gift':
            line_items.append({
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': f"Gift Wrap: {item['gift'].name}",
                    },
                    'unit_amount': int(item['price'] * 100),
                },
                'quantity': 1,
            })

    discounted_total = order.get_discounted_total()
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri('/payment/stripe/success/') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri('/payment/stripe/cancel/') + f'?order_id={order.id}',
            metadata={
                'order_id': order.id
            }
        )
        order.stripe_payment_intent_id = checkout_session.payment_intent
        order.payment_provider = 'stripe'
        order.save()
        return checkout_session
    except Exception as e:
        logger.error(f"Error creating Stripe session: {str(e)}")
        raise


# Добавляем фиксированный обменный курс (замените на актуальный или используйте API)
EUR_TO_RUB_RATE = Decimal('100.00')  # 1 EUR = 100 RUB, настройте по вашим требованиям

def create_yookassa_payment(order, request):
    cart = Cart(request)
    receipt_items = []
    for item in cart:
        if item['type'] == 'product':
            price_in_rub = item['price'] * EUR_TO_RUB_RATE
            receipt_items.append({
                "description": f"{item['perfume'].name} - {item['capacity'].volume}",
                "quantity": str(item['quantity']),
                "amount": {
                    "value": f"{price_in_rub:.2f}",
                    "currency": "RUB"  # Изменено на RUB
                },
                "vat_code": getattr(settings, 'YOOKASSA_VAT_CODE', 1),
                "payment_mode": "full_payment",
                "payment_subject": "commodity"
            })
        elif item['type'] == 'gift':
            price_in_rub = item['price'] * EUR_TO_RUB_RATE
            receipt_items.append({
                "description": f"Gift Wrap: {item['gift'].name}",
                "quantity": "1",
                "amount": {
                    "value": f"{price_in_rub:.2f}",
                    "currency": "RUB"  # Изменено на RUB
                },
                "vat_code": getattr(settings, 'YOOKASSA_VAT_CODE', 1),
                "payment_mode": "full_payment",
                "payment_subject": "commodity"
            })

    customer = {
        "email": order.email,
        "phone": order.phone
    }

    discounted_total = order.get_discounted_total()
    discounted_total_rub = discounted_total * EUR_TO_RUB_RATE

    try:
        payment = Payment.create({
            "amount": {
                "value": f"{discounted_total_rub:.2f}",
                "currency": "RUB"  # Изменено на RUB
            },
            "confirmation": {
                "type": "redirect",
                "return_url": request.build_absolute_uri('/payment/yookassa/success/') + f'?order_id={order.id}'
            },
            "capture": True,
            "description": f"Order #{order.id}",
            "metadata": {
                "order_id": order.id,
                "user_id": order.user.id
            },
            "receipt": {
                "customer": customer,
                "items": receipt_items
            }
        }, str(order.id))

        order.yookassa_payment_id = payment.id
        order.payment_provider = 'yookassa'
        order.save()
        return payment
    except Exception as e:
        logger.error(f"Error creating Yookassa payment: {str(e)}")
        raise


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, stripe_endpoint_secret
        )
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {str(e)}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook signature verification failed: {str(e)}")
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session['metadata'].get('order_id')
        try:
            order = Order.objects.get(id=order_id)
            order.status = 'processing'
            order.stripe_payment_intent_id = session.get('payment_intent')
            order.save()
            logger.info(f"Order {order_id} updated: status=processing, stripe_payment_intent_id={order.stripe_payment_intent_id}")

            cart = Cart(request)
            cart.clear()

            for key in ['promo_code', 'discount_percentage', 'promo_message']:
                if key in request.session:
                    del request.session[key]
                    logger.debug(f"Cleared session key: {key}")
        except Order.DoesNotExist:
            logger.error(f"Order {order_id} not found")
            return HttpResponse(status=404)

    return HttpResponse(status=200)


@csrf_exempt
@require_POST
def yookassa_webhook(request):
    if request.method != 'POST':
        logger.warning(f"Invalid request method: {request.method}")
        return HttpResponseNotAllowed(['POST'])

    logger.info(f"Yookassa webhook received | IP: {request.META.get('REMOTE_ADDR')} | User-Agent: {request.META.get('HTTP_USER_AGENT')}")

    try:
        raw_body = request.body.decode('utf-8')
        event_json = json.loads(raw_body)
        event_type = event_json.get('event')
        payment = event_json.get('object', {})
        payment_id = payment.get('id')

        logger.info(f"Processing Yookassa event: {event_type} | Payment ID: {payment_id}")

        metadata = payment.get('metadata', {})
        order_id = metadata.get('order_id')
        user_id = metadata.get('user_id')

        if not all([order_id, user_id]):
            logger.error(f"Missing metadata: order_id={order_id}, user_id={user_id}")
            return HttpResponseBadRequest("Missing required metadata")

        order = Order.objects.select_for_update().get(id=order_id, user_id=user_id)

        if event_type == 'payment.succeeded':
            if payment.get('status') == 'succeeded':
                if order.status == 'processing':
                    logger.info(f"Order {order_id} already processed, skipping")
                    return HttpResponse(status=200)
                
                order.status = 'processing'
                order.yookassa_payment_id = payment_id
                order.save()
                logger.info(f"Order {order_id} successfully processed")

                cart = Cart(request)
                cart.clear()

                for key in ['promo_code', 'discount_percentage', 'promo_message']:
                    if key in request.session:
                        del request.session[key]
                        logger.debug(f"Cleared session key: {key}")

        elif event_type == 'payment.canceled':
            if payment.get('status') == 'canceled':
                if order.status == 'cancelled':
                    logger.info(f"Order {order_id} already cancelled, skipping")
                    return HttpResponse(status=200)
                
                order.status = 'cancelled'
                order.save()
                logger.info(f"Order {order_id} marked as cancelled")

        return HttpResponse(status=200)

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return HttpResponseBadRequest("Invalid JSON")
    except Order.DoesNotExist:
        logger.error(f"Order not found: order_id={order_id}, user_id={user_id}")
        return HttpResponseBadRequest("Order not found")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return HttpResponse(status=500)


def stripe_success(request):
    session_id = request.GET.get('session_id')
    if session_id:
        session = stripe.checkout.Session.retrieve(session_id)
        order_id = session.metadata['order_id']
        order = Order.objects.get(id=order_id)
        return render(request, 'payment/stripe_success.html', {'order': order})
    return redirect('main:home')


def stripe_cancel(request):
    order_id = request.GET.get('order_id')
    if order_id:
        order = get_object_or_404(Order, id=order_id)
        order.status = 'cancelled'
        order.save()
        return render(request, 'payment/stripe_cancel.html', {'order': order})
    return redirect('orders:checkout')


def yookassa_success(request):
    order_id = request.GET.get('order_id')
    if order_id:
        order = get_object_or_404(Order, id=order_id)
        if order.status == 'processing':
            return render(request, 'payment/yookassa_success.html', {'order': order})
        elif order.status == 'cancelled':
            return redirect('payment:yookassa_cancel')
        if order.yookassa_payment_id:
            try:
                payment = Payment.find_one(order.yookassa_payment_id)
                if payment.status == 'succeeded':
                    order.status = 'processing'
                    order.save()
                    return render(request, 'payment/yookassa_success.html', {'order': order})
                elif payment.status in ['canceled', 'failed']:
                    order.status = 'cancelled'
                    order.save()
                    return redirect('payment:yookassa_cancel')
            except Exception as e:
                logger.error(f"Yookassa payment check error: {str(e)}")
    return render(request, 'payment/yookassa_pending.html', {'order': order})


def yookassa_cancel(request):
    order_id = request.GET.get('order_id')
    if order_id:
        order = get_object_or_404(Order, id=order_id)
        order.status = 'cancelled'
        order.save()
        return render(request, 'payment/yookassa_cancel.html', {'order': order})
    return redirect('orders:checkout')
