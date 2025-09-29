from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Order, OrderItem, OrderSample, OrderGift


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('image_preview', 'perfume', 'capacity', 'quantity', 'price', 'get_total_price')
    readonly_fields = ('image_preview', 'get_total_price')
    can_delete = False


    def image_preview(self, obj):
        if obj.perfume.image:
            return mark_safe(f'<img src="{obj.perfume.image.url}" style="max-height: 100px; max-width: 100px; object-fit: cover;" />')
        return mark_safe('<span style="color: gray;">No image</span>')
    image_preview.short_description = 'Image'


    def get_total_price(self, obj):
        try:
            return obj.get_total_price()
        except TypeError:
            return mark_safe('<span style="color: red;">Invalid data</span>')
    get_total_price.short_description = 'Total Price'


class OrderSampleInline(admin.TabularInline):
    model = OrderSample
    extra = 0
    fields = ('image_preview', 'sample')
    readonly_fields = ('image_preview',)
    can_delete = False


    def image_preview(self, obj):
        if obj.sample.image:
            return mark_safe(f'<img src="{obj.sample.image.url}" style="max-height: 100px; max-width: 100px; object-fit: cover;" />')
        return mark_safe('<span style="color: gray;">No image</span>')
    image_preview.short_description = 'Image'


class OrderGiftInline(admin.TabularInline):
    model = OrderGift
    extra = 0
    fields = ('image_preview', 'gift', 'price')
    readonly_fields = ('image_preview',)
    can_delete = False


    def image_preview(self, obj):
        if obj.gift.image:
            return mark_safe(f'<img src="{obj.gift.image.url}" style="max-height: 100px; max-width: 100px; object-fit: cover;" />')
        return mark_safe('<span style="color: gray;">No image</span>')
    image_preview.short_description = 'Image'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'email', 'total_price', 'payment_provider', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'payment_provider', 'created_at')
    search_fields = ('email', 'first_name', 'last_name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'total_price', 'discount_percentage', 'stripe_payment_intent_id', 'yookassa_payment_id', 'get_discounted_total')
    inlines = [OrderItemInline, OrderSampleInline, OrderGiftInline]

    fieldsets = (
        ('Order Information', {
            'fields': ('user', 'first_name', 'last_name', 'email', 'company', 'address1', 'address2', 'city', 'country', 'province', 'postal_code', 'phone', 'special_instructions', 'promo_code', 'discount_percentage', 'total_price', 'get_discounted_total')
        }),
        ('Payment and Status', {
            'fields': ('status', 'payment_provider', 'stripe_payment_intent_id', 'yookassa_payment_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


    def get_discounted_total(self, obj):
        return obj.get_discounted_total()
    get_discounted_total.short_description = 'Discounted Total'


    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('user', 'first_name', 'last_name', 'email', 'company', 'address1', 'address2', 'city', 'country', 'province', 'postal_code', 'phone', 'promo_code')
        return self.readonly_fields
