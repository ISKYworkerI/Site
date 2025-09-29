from django.db import models
from django.conf import settings
from main.models import Perfume, Capacity, PerfumeCapacity
from samples.models import Sample
from gifts.models import Gift
from promo.models import PromoCode
from decimal import Decimal


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    PAYMENT_PROVIDER_CHOICES = (
        ('stripe', 'Stripe'),
        ('yookassa', 'Yookassa'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(max_length=254)
    company = models.CharField(max_length=100, blank=True, null=True)
    address1 = models.CharField(max_length=255, blank=True, null=True)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    special_instructions = models.TextField(blank=True)
    promo_code = models.ForeignKey(PromoCode, on_delete=models.SET_NULL, null=True, blank=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_provider = models.CharField(max_length=20, choices=PAYMENT_PROVIDER_CHOICES, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    yookassa_payment_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"Order {self.id} by {self.email}"


    def get_discounted_total(self):
        if self.total_price is None:
            return 0  
        if self.discount_percentage > 0:
            return round(self.total_price * (1 - (self.discount_percentage / 100)), 2)
        return round(self.total_price, 2)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    perfume = models.ForeignKey(Perfume, on_delete=models.CASCADE)
    capacity = models.ForeignKey(Capacity, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)


    def __str__(self):
        return f"{self.perfume.name} - {self.capacity.volume} ({self.quantity})"


    def get_total_price(self):
        return self.price * self.quantity


class OrderSample(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='samples')
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE)


    def __str__(self):
        return f"Sample {self.sample.name} for Order {self.order.id}"


class OrderGift(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='gift', null=True, blank=True)
    gift = models.ForeignKey(Gift, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)


    def __str__(self):
        return f"Gift {self.gift.name} for Order {self.order.id}"
    