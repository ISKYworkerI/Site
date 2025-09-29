from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('stripe/success/', views.stripe_success, name='stripe_success'),
    path('stripe/cancel/', views.stripe_cancel, name='stripe_cancel'),
    path('yookassa/webhook/', views.yookassa_webhook, name='yookassa_webhook'),
    path('yookassa/success/', views.yookassa_success, name='yookassa_success'),
    path('yookassa/cancel/', views.yookassa_cancel, name='yookassa_cancel'),
]
