from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .cart import Cart
from main.models import Perfume, PerfumeCapacity, Capacity
from promo.models import PromoCode
from promo.forms import PromoCodeForm
from decimal import Decimal
from samples.models import Sample
from gifts.models import Gift
import logging

logger = logging.getLogger(__name__)

def cart_detail(request):
    cart = Cart(request)
    promo_form = PromoCodeForm()
    discount = Decimal(0)
    promo_message = ""
    samples = Sample.objects.filter(available=True)
    gifts = Gift.objects.filter(available=True)
    special_instructions = cart.cart.get('special_instructions', '')

    if request.method == 'POST' and 'special_instructions' in request.POST:
        instructions = request.POST.get('special_instructions', '')
        cart.set_special_instructions(instructions)
        return render(request, 'cart/partials/special_instructions_content.html', {
            'special_instructions': instructions
        })

    if request.method == 'POST' and 'code' in request.POST:
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
            request.session['promo_message'] = promo_message
        return render(request, 'cart/partials/cart_summary.html', {
            'cart': cart,
            'promo_form': promo_form,
            'discount': discount,
            'total_price': cart.get_total_price(),
            'discounted_price': cart.get_total_price() * (Decimal(1) - discount / Decimal(100)),
            'promo_message': promo_message,
        })

    total_price = cart.get_total_price()
    discount = Decimal(request.session.get('discount_percentage', 0))
    discounted_price = total_price * (Decimal(1) - discount / Decimal(100))

    logger.debug(f"Cart detail: total_price={total_price}, discounted_price={discounted_price}, discount={discount}")

    return render(request, 'cart/cart_detail.html', {
        'cart': cart,
        'promo_form': promo_form,
        'discount': discount,
        'total_price': total_price,
        'discounted_price': discounted_price,
        'promo_message': promo_message,
        'samples': samples,
        'gifts': gifts,
        'gift_wrap': cart.get_gift_wrap(),
        'special_instructions': special_instructions,
    })

def sample_counter(request):
    cart = Cart(request)
    logger.debug(f"Rendering sample counter: samples={cart.cart['samples']}")
    return render(request, 'cart/partials/sample_counter.html', {
        'cart': cart,
    })

def cart_summary(request):
    cart = Cart(request)
    total_price = cart.get_total_price()
    discount = Decimal(request.session.get('discount_percentage', 0))
    discounted_price = total_price * (Decimal(1) - discount / Decimal(100))
    promo_form = PromoCodeForm()
    promo_message = request.session.get('promo_message', '')

    logger.debug(f"Rendering cart summary: total_price={total_price}, discounted_price={discounted_price}, discount={discount}")

    return render(request, 'cart/partials/cart_summary.html', {
        'cart': cart,
        'total_price': total_price,
        'discounted_price': discounted_price,
        'discount': discount,
        'promo_form': promo_form,
        'promo_message': promo_message,
    })

def cart_items(request):
    cart = Cart(request)
    logger.debug(f"Rendering cart items: items={len(cart.cart['products'])}, samples={len(cart.cart['samples'])}, gift_wrap={cart.cart['gift_wrap']}")
    return render(request, 'cart/partials/cart_items.html', {
        'cart': cart,
    })

def cart_add(request, perfume_id):
    if request.method == 'POST':
        cart = Cart(request)
        perfume = get_object_or_404(Perfume, id=perfume_id)
        capacity_id = request.POST.get('capacity')
        quantity = int(request.POST.get('quantity', 1))
        override = request.POST.get('override', False) == 'True'

        if not capacity_id:
            logger.warning(f"No capacity_id provided for perfume_id={perfume_id}")
            return redirect('main:perfume_detail', slug=perfume.slug)

        try:
            capacity = Capacity.objects.get(id=capacity_id)
            perfume_capacity = PerfumeCapacity.objects.get(perfume=perfume, capacity=capacity)
            
            if not perfume_capacity.available or perfume_capacity.quantity < quantity:
                logger.warning(f"Perfume capacity unavailable or insufficient: perfume_id={perfume_id}, capacity_id={capacity_id}, quantity={quantity}")
                return redirect('main:perfume_detail', slug=perfume.slug)
        except (Capacity.DoesNotExist, PerfumeCapacity.DoesNotExist) as e:
            logger.error(f"Error accessing capacity or perfume_capacity: {e}")
            return redirect('main:perfume_detail', slug=perfume.slug)

        cart.add(perfume, capacity, quantity, override_quantity=override)
        logger.info(f"Added to cart: perfume_id={perfume_id}, capacity_id={capacity_id}, quantity={quantity}")
        
        if request.headers.get('HX-Request') == 'true':
            return render(request, 'cart/partials/cart_modal.html', {
                'cart': cart,
                'total_price': cart.get_total_price(),
                'discounted_price': cart.get_total_price() * (Decimal(1) - Decimal(request.session.get('discount_percentage', 0)) / Decimal(100)),
                'discount': Decimal(request.session.get('discount_percentage', 0)),
                'promo_form': PromoCodeForm(),
                'promo_message': request.session.get('promo_message', ''),
                'samples': Sample.objects.filter(available=True),
                'gifts': Gift.objects.filter(available=True),
                'gift_wrap': cart.get_gift_wrap(),
                'special_instructions': cart.cart.get('special_instructions', ''),
            })
        
        response = redirect('main:perfume_detail', slug=perfume.slug)
        response.set_cookie('show_cart_modal', 'true')
        return response
    
    return redirect('main:home')

def cart_remove(request, perfume_id, capacity_id):
    cart = Cart(request)
    perfume = get_object_or_404(Perfume, id=perfume_id)
    capacity = get_object_or_404(Capacity, id=capacity_id)
    
    cart.remove(perfume, capacity)
    cart.remove_all_samples()
    cart.remove_gift_wrap()
    logger.info(f"Removed from cart: perfume_id={perfume_id}, capacity_id={capacity_id}, cleared samples and gift")

    if request.headers.get('HX-Request') == 'true':
        is_modal = request.POST.get('is_modal') == 'true'
        if is_modal:
            return render(request, 'cart/partials/cart_modal.html', {
                'cart': cart,
                'total_price': cart.get_total_price(),
                'discounted_price': cart.get_total_price() * (Decimal(1) - Decimal(request.session.get('discount_percentage', 0)) / Decimal(100)),
                'discount': Decimal(request.session.get('discount_percentage', 0)),
                'promo_form': PromoCodeForm(),
                'promo_message': request.session.get('promo_message', ''),
                'samples': Sample.objects.filter(available=True),
                'gifts': Gift.objects.filter(available=True),
                'gift_wrap': cart.get_gift_wrap(),
                'special_instructions': cart.cart.get('special_instructions', ''),
            })
        else:
            return HttpResponse(
                headers={
                    'HX-Trigger': '{"updateCartItems": "", "updateSampleCounter": "", "updateCartSummary": ""}',
                },
                content=render(request, 'cart/partials/cart_items.html', {
                    'cart': cart,
                }).content
            )
        
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('main:home')

def cart_update_quantity(request, perfume_id, capacity_id):
    if request.method == 'POST':
        cart = Cart(request)
        perfume = get_object_or_404(Perfume, id=perfume_id)
        capacity = get_object_or_404(Capacity, id=capacity_id)
        quantity = int(request.POST.get('quantity', 1))

        try:
            perfume_capacity = PerfumeCapacity.objects.get(perfume=perfume, capacity=capacity)
            if not perfume_capacity.available or perfume_capacity.quantity < quantity:
                logger.warning(f"Quantity not available: perfume_id={perfume_id}, capacity_id={capacity_id}, requested={quantity}")
                is_modal = request.POST.get('is_modal') == 'true'
                if is_modal:
                    return render(request, 'cart/partials/cart_modal.html', {
                        'cart': cart,
                        'total_price': cart.get_total_price(),
                        'discounted_price': cart.get_total_price() * (Decimal(1) - Decimal(request.session.get('discount_percentage', 0)) / Decimal(100)),
                        'discount': Decimal(request.session.get('discount_percentage', 0)),
                        'promo_form': PromoCodeForm(),
                        'promo_message': 'Requested quantity not available',
                        'samples': Sample.objects.filter(available=True),
                        'gifts': Gift.objects.filter(available=True),
                        'gift_wrap': cart.get_gift_wrap(),
                        'special_instructions': cart.cart.get('special_instructions', ''),
                    })
                else:
                    return render(request, 'cart/partials/cart_item.html', {
                        'item': next(item for item in cart if item['type'] == 'product' and item['perfume'].id == perfume_id and item['capacity'].id == capacity_id),
                        'error': 'Requested quantity not available'
                    })
        except PerfumeCapacity.DoesNotExist:
            logger.error(f"PerfumeCapacity not found: perfume_id={perfume_id}, capacity_id={capacity_id}")
            is_modal = request.POST.get('is_modal') == 'true'
            if is_modal:
                return render(request, 'cart/partials/cart_modal.html', {
                    'cart': cart,
                    'total_price': cart.get_total_price(),
                    'discounted_price': cart.get_total_price() * (Decimal(1) - Decimal(request.session.get('discount_percentage', 0)) / Decimal(100)),
                    'discount': Decimal(request.session.get('discount_percentage', 0)),
                    'promo_form': PromoCodeForm(),
                    'promo_message': 'Capacity not found',
                    'samples': Sample.objects.filter(available=True),
                    'gifts': Gift.objects.filter(available=True),
                    'gift_wrap': cart.get_gift_wrap(),
                    'special_instructions': cart.cart.get('special_instructions', ''),
                })
            else:
                return render(request, 'cart/partials/cart_item.html', {
                    'item': next(item for item in cart if item['type'] == 'product' and item['perfume'].id == perfume_id and item['capacity'].id == capacity_id),
                    'error': 'Capacity not found'
                })

        cart.add(perfume, capacity, quantity, override_quantity=True)
        logger.info(f"Updated quantity: perfume_id={perfume_id}, capacity_id={capacity_id}, quantity={quantity}")

        if request.headers.get('HX-Request') == 'true':
            is_modal = request.POST.get('is_modal') == 'true'
            if is_modal:
                return render(request, 'cart/partials/cart_modal.html', {
                    'cart': cart,
                    'total_price': cart.get_total_price(),
                    'discounted_price': cart.get_total_price() * (Decimal(1) - Decimal(request.session.get('discount_percentage', 0)) / Decimal(100)),
                    'discount': Decimal(request.session.get('discount_percentage', 0)),
                    'promo_form': PromoCodeForm(),
                    'promo_message': request.session.get('promo_message', ''),
                    'samples': Sample.objects.filter(available=True),
                    'gifts': Gift.objects.filter(available=True),
                    'gift_wrap': cart.get_gift_wrap(),
                    'special_instructions': cart.cart.get('special_instructions', ''),
                })
            else:
                return HttpResponse(
                    headers={
                        'HX-Trigger': '{"updateCartItems": "", "updateSampleCounter": "", "updateCartSummary": ""}',
                    },
                    content=render(request, 'cart/partials/cart_item.html', {
                        'item': next(item for item in cart if item['type'] == 'product' and item['perfume'].id == perfume_id and item['capacity'].id == capacity_id)
                    }).content
                )
    
    return redirect(request.META.get('HTTP_REFERER', 'main:home'))

def cart_add_sample(request, sample_id):
    cart = Cart(request)
    sample = get_object_or_404(Sample, id=sample_id)
    
    if not cart.cart['products']:
        logger.info(f"Cannot add sample: sample_id={sample_id}, no items in cart")
        is_modal = request.POST.get('is_modal') == 'true'
        if is_modal:
            return render(request, 'cart/partials/cart_modal.html', {
                'cart': cart,
                'total_price': cart.get_total_price(),
                'discounted_price': cart.get_total_price() * (Decimal(1) - Decimal(request.session.get('discount_percentage', 0)) / Decimal(100)),
                'discount': Decimal(request.session.get('discount_percentage', 0)),
                'promo_form': PromoCodeForm(),
                'promo_message': 'Cannot add sample: cart is empty',
                'samples': Sample.objects.filter(available=True),
                'gifts': Gift.objects.filter(available=True),
                'gift_wrap': cart.get_gift_wrap(),
                'special_instructions': cart.cart.get('special_instructions', ''),
            })
        else:
            return HttpResponse(
                headers={
                    'HX-Trigger': '{"updateCartItems": "", "updateSampleCounter": "", "updateCartSummary": ""}',
                },
                content=render(request, 'cart/partials/cart_items.html', {
                    'cart': cart,
                }).content
            )
    
    if str(sample_id) in cart.cart['samples']:
        cart.remove_sample(sample_id)
        logger.info(f"Removed sample: sample_id={sample_id}")
    else:
        cart.replace_sample(sample_id)
        logger.info(f"Added sample: sample_id={sample_id}")

    if request.headers.get('HX-Request') == 'true':
        is_modal = request.POST.get('is_modal') == 'true'
        if is_modal:
            return render(request, 'cart/partials/cart_modal.html', {
                'cart': cart,
                'total_price': cart.get_total_price(),
                'discounted_price': cart.get_total_price() * (Decimal(1) - Decimal(request.session.get('discount_percentage', 0)) / Decimal(100)),
                'discount': Decimal(request.session.get('discount_percentage', 0)),
                'promo_form': PromoCodeForm(),
                'promo_message': request.session.get('promo_message', ''),
                'samples': Sample.objects.filter(available=True),
                'gifts': Gift.objects.filter(available=True),
                'gift_wrap': cart.get_gift_wrap(),
                'special_instructions': cart.cart.get('special_instructions', ''),
            })
        else:
            return HttpResponse(
                headers={
                    'HX-Trigger': '{"updateCartItems": "", "updateSampleCounter": "", "updateCartSummary": ""}',
                },
                content=render(request, 'cart/partials/cart_items.html', {
                    'cart': cart,
                }).content
            )
    
    return redirect('cart:cart_detail')

def cart_remove_sample(request, sample_id):
    cart = Cart(request)
    cart.remove_sample(sample_id)
    logger.info(f"Removed sample: sample_id={sample_id}")
    
    if request.headers.get('HX-Request') == 'true':
        is_modal = request.POST.get('is_modal') == 'true'
        if is_modal:
            return render(request, 'cart/partials/cart_modal.html', {
                'cart': cart,
                'total_price': cart.get_total_price(),
                'discounted_price': cart.get_total_price() * (Decimal(1) - Decimal(request.session.get('discount_percentage', 0)) / Decimal(100)),
                'discount': Decimal(request.session.get('discount_percentage', 0)),
                'promo_form': PromoCodeForm(),
                'promo_message': request.session.get('promo_message', ''),
                'samples': Sample.objects.filter(available=True),
                'gifts': Gift.objects.filter(available=True),
                'gift_wrap': cart.get_gift_wrap(),
                'special_instructions': cart.cart.get('special_instructions', ''),
            })
        else:
            return HttpResponse(
                headers={
                    'HX-Trigger': '{"updateCartItems": "", "updateSampleCounter": "", "updateCartSummary": ""}',
                },
                content=render(request, 'cart/partials/cart_items.html', {
                    'cart': cart,
                }).content
            )
        
    return redirect(request.META.get('HTTP_REFERER', 'cart:cart_detail'))

def cart_add_gift(request, gift_id):
    cart = Cart(request)
    gift = get_object_or_404(Gift, id=gift_id)
    
    if not cart.cart['products']:
        logger.info(f"Cannot add gift: gift_id={gift_id}, no items in cart")
        is_modal = request.POST.get('is_modal') == 'true'
        if is_modal:
            return render(request, 'cart/partials/cart_modal.html', {
                'cart': cart,
                'total_price': cart.get_total_price(),
                'discounted_price': cart.get_total_price() * (Decimal(1) - Decimal(request.session.get('discount_percentage', 0)) / Decimal(100)),
                'discount': Decimal(request.session.get('discount_percentage', 0)),
                'promo_form': PromoCodeForm(),
                'promo_message': 'Cannot add gift: cart is empty',
                'samples': Sample.objects.filter(available=True),
                'gifts': Gift.objects.filter(available=True),
                'gift_wrap': cart.get_gift_wrap(),
                'special_instructions': cart.cart.get('special_instructions', ''),
            })
        else:
            return HttpResponse(
                headers={
                    'HX-Trigger': '{"updateCartItems": "", "updateSampleCounter": "", "updateCartSummary": ""}',
                },
                content=render(request, 'cart/partials/cart_items.html', {
                    'cart': cart,
                }).content
            )
    
    if cart.cart['gift_wrap'] == str(gift_id):
        cart.remove_gift_wrap()
        logger.info(f"Removed gift wrap: gift_id={gift_id}")
    else:
        cart.set_gift_wrap(gift_id)
        logger.info(f"Added gift wrap: gift_id={gift_id}")

    if request.headers.get('HX-Request') == 'true':
        is_modal = request.POST.get('is_modal') == 'true'
        if is_modal:
            return render(request, 'cart/partials/cart_modal.html', {
                'cart': cart,
                'total_price': cart.get_total_price(),
                'discounted_price': cart.get_total_price() * (Decimal(1) - Decimal(request.session.get('discount_percentage', 0)) / Decimal(100)),
                'discount': Decimal(request.session.get('discount_percentage', 0)),
                'promo_form': PromoCodeForm(),
                'promo_message': request.session.get('promo_message', ''),
                'samples': Sample.objects.filter(available=True),
                'gifts': Gift.objects.filter(available=True),
                'gift_wrap': cart.get_gift_wrap(),
                'special_instructions': cart.cart.get('special_instructions', ''),
            })
        else:
            return HttpResponse(
                headers={
                    'HX-Trigger': '{"updateCartItems": "", "updateSampleCounter": "", "updateCartSummary": ""}',
                },
                content=render(request, 'cart/partials/cart_items.html', {
                    'cart': cart,
                }).content
            )
    
    return redirect('cart:cart_detail')

def cart_remove_gift(request):
    cart = Cart(request)
    cart.remove_gift_wrap()
    logger.info("Removed gift wrap")

    if request.headers.get('HX-Request') == 'true':
        is_modal = request.POST.get('is_modal') == 'true'
        if is_modal:
            return render(request, 'cart/partials/cart_modal.html', {
                'cart': cart,
                'total_price': cart.get_total_price(),
                'discounted_price': cart.get_total_price() * (Decimal(1) - Decimal(request.session.get('discount_percentage', 0)) / Decimal(100)),
                'discount': Decimal(request.session.get('discount_percentage', 0)),
                'promo_form': PromoCodeForm(),
                'promo_message': request.session.get('promo_message', ''),
                'samples': Sample.objects.filter(available=True),
                'gifts': Gift.objects.filter(available=True),
                'gift_wrap': cart.get_gift_wrap(),
                'special_instructions': cart.cart.get('special_instructions', ''),
            })
        else:
            return HttpResponse(
                headers={
                    'HX-Trigger': '{"updateCartItems": "", "updateSampleCounter": "", "updateCartSummary": ""}',
                },
                content=render(request, 'cart/partials/cart_items.html', {
                    'cart': cart,
                }).content
            )
        
    return redirect(request.META.get('HTTP_REFERER', 'cart:cart_detail'))

def cart_modal(request):
    cart = Cart(request)
    total_price = cart.get_total_price()
    discount = Decimal(request.session.get('discount_percentage', 0))
    discounted_price = total_price * (Decimal(1) - discount / Decimal(100))
    return render(request, 'cart/partials/cart_modal.html', {
        'cart': cart,
        'total_price': total_price,
        'discounted_price': discounted_price,
        'discount': discount,
        'promo_form': PromoCodeForm(),
        'promo_message': request.session.get('promo_message', ''),
        'samples': Sample.objects.filter(available=True),
        'gifts': Gift.objects.filter(available=True),
        'gift_wrap': cart.get_gift_wrap(),
        'special_instructions': cart.cart.get('special_instructions', ''),
    })