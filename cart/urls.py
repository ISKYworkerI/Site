from django.urls import path
from .views import (
    cart_detail, cart_add, cart_remove, cart_update_quantity, cart_remove_sample,
    cart_remove_gift, cart_modal, cart_add_sample, cart_add_gift,
    sample_counter, cart_summary, cart_items
)

app_name = 'cart'

urlpatterns = [
    path('', cart_detail, name='cart_detail'),
    path('add/<int:perfume_id>/', cart_add, name='cart_add'),
    path('remove/<int:perfume_id>/<int:capacity_id>/', cart_remove, name='cart_remove'),
    path('update/<int:perfume_id>/<int:capacity_id>/', cart_update_quantity, name='cart_update_quantity'),
    path('add_sample/<int:sample_id>/', cart_add_sample, name='cart_add_sample'),
    path('remove_sample/<int:sample_id>/', cart_remove_sample, name='cart_remove_sample'),
    path('add_gift/<int:gift_id>/', cart_add_gift, name='cart_add_gift'),
    path('remove_gift/', cart_remove_gift, name='cart_remove_gift'),
    path('modal/', cart_modal, name='cart_modal'),
    path('sample_counter/', sample_counter, name='sample_counter'),
    path('summary/', cart_summary, name='cart_summary'),
    path('items/', cart_items, name='cart_items'),
]