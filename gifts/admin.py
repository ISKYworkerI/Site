from django.contrib import admin
from .models import Gift
from django.utils.safestring import mark_safe

class GiftAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_image', 'price', 'available', 'created_at')
    list_filter = ('available', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('get_image',)
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'price', 'available')
        }),
        ('Изображение', {
            'fields': ('image', 'get_image'),
        }),
    )


    def get_image(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="50" height="50" />')
        return "Нет изображения"
    get_image.short_description = "Изображение"


admin.site.register(Gift, GiftAdmin)
