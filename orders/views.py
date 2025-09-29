from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import OrderForm
from .models import Order, OrderItem, OrderSample, OrderGift
from cart.cart import Cart
from promo.models import PromoCode
from promo.forms import PromoCodeForm
from decimal import Decimal
import logging
from payment.views import create_stripe_checkout_session, create_yookassa_payment

logger = logging.getLogger(__name__)


@login_required(login_url='/users/login')
def checkout(request):
    cart = Cart(request)
    if not cart:
        logger.warning("Empty cart, redirecting to cart_detail")
        return redirect('cart:cart_detail')

    total_price = cart.get_total_price()
    discount = Decimal(0)
    promo_message = ""
    promo_form = PromoCodeForm()

    if 'promo_code' in request.session:
        try:
            promo = PromoCode.objects.get(code=request.session['promo_code'], is_active=True)
            discount = promo.discount_percentage
        except PromoCode.DoesNotExist:
            logger.warning("Invalid promo code in session, clearing")
            del request.session['promo_code']
            if 'discount_percentage' in request.session:
                del request.session['discount_percentage']

    if request.method == 'POST' and 'apply_promo' in request.POST:
        promo_form = PromoCodeForm(request.POST)
        if promo_form.is_valid():
            code = promo_form.cleaned_data['code']
            try:
                promo = PromoCode.objects.get(code=code, is_active=True)
                discount = promo.discount_percentage
                promo_message = "Promo code applied successfully!"
                request.session['promo_code'] = promo.code
                request.session['discount_percentage'] = str(discount)
            except PromoCode.DoesNotExist:
                promo_message = "Invalid or inactive promo code."
                if 'promo_code' in request.session:
                    del request.session['promo_code']
                if 'discount_percentage' in request.session:
                    del request.session['discount_percentage']
                discount = Decimal(0)

        discounted_price = total_price * (Decimal(1) - discount / Decimal(100))
        return render(request, 'orders/partials/summary.html', {
            'cart': cart,
            'total_price': total_price,
            'discount': discount,
            'discounted_price': discounted_price,
            'promo_message': promo_message,
        })

    if request.method == 'POST' and 'create_order' in request.POST:
        form_data = request.POST.copy()
        if not form_data.get('email'):
            form_data['email'] = request.user.email
        form = OrderForm(form_data, user=request.user)
        payment_provider = request.POST.get('payment_provider', 'stripe')

        if form.is_valid():
            order = Order.objects.create(
                user=request.user,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                company=form.cleaned_data['company'],
                address1=form.cleaned_data['address1'],
                address2=form.cleaned_data['address2'],
                city=form.cleaned_data['city'],
                country=form.cleaned_data['country'],
                province=form.cleaned_data['province'],
                postal_code=form.cleaned_data['postal_code'],
                phone=form.cleaned_data['phone'],
                special_instructions=cart.cart.get('special_instructions', ''),
                total_price=total_price,
                discount_percentage=discount,
            )

            if 'promo_code' in request.session:
                try:
                    promo = PromoCode.objects.get(code=request.session['promo_code'], is_active=True)
                    order.promo_code = promo
                    order.save()
                except PromoCode.DoesNotExist:
                    logger.warning("Promo code not found during order creation")

            for item in cart:
                logger.debug(f"Processing cart item: {item}")
                if item['type'] == 'product':
                    OrderItem.objects.create(
                        order=order,
                        perfume=item['perfume'],
                        capacity=item['capacity'],
                        quantity=item['quantity'],
                        price=item['price'] or Decimal('0.00')
                    )
                elif item['type'] == 'sample':
                    OrderSample.objects.create(
                        order=order,
                        sample=item['sample']
                    )
                elif item['type'] == 'gift':
                    OrderGift.objects.create(
                        order=order,
                        gift=item['gift'],
                        price=item['price'] or Decimal('0.00')
                    )

            try:
                if payment_provider == 'stripe':
                    checkout_session = create_stripe_checkout_session(order, request)
                    cart.clear()
                    return redirect(checkout_session.url)
                elif payment_provider == 'yookassa':
                    payment = create_yookassa_payment(order, request)
                    cart.clear()
                    return redirect(payment.confirmation.confirmation_url)
            except Exception as e:
                logger.error(f"Error creating payment: {str(e)}")
                order.delete()
                discounted_price = total_price * (Decimal(1) - discount / Decimal(100))
                return render(request, 'orders/checkout.html', {
                    'form': form,
                    'cart': cart,
                    'promo_form': promo_form,
                    'discount': discount,
                    'total_price': total_price,
                    'discounted_price': discounted_price,
                    'promo_message': f'Error processing payment: {str(e)}',
                })
        else:
            logger.warning(f"Form validation failed: {form.errors}")
            discounted_price = total_price * (Decimal(1) - discount / Decimal(100))
            return render(request, 'orders/checkout.html', {
                'form': form,
                'cart': cart,
                'promo_form': promo_form,
                'discount': discount,
                'total_price': total_price,
                'discounted_price': discounted_price,
                'promo_message': 'Please correct the errors in the form.',
            })

    else:
        form = OrderForm(user=request.user)

    discounted_price = total_price * (Decimal(1) - discount / Decimal(100))

    return render(request, 'orders/checkout.html', {
        'form': form,
        'cart': cart,
        'promo_form': promo_form,
        'discount': discount,
        'total_price': total_price,
        'discounted_price': discounted_price,
        'promo_message': promo_message,
    })