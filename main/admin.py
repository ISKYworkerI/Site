from django.contrib import admin
from django import forms
from .models import Capacity, Category, Perfume, PerfumeCapacity, PerfumeImage, \
    OlfactoryNote, OlfactoryNoteCategory, OlfactoryFamily, Ingredient
from adminsortable2.admin import SortableAdminMixin


@admin.action(description='Сжать выбранные изображения')
def compress_selected_images(modeladmin, request, queryset):
    for image in queryset:
        image.save()
    modeladmin.message_user(request, "Изображения успешно сжаты.")


class PerfumeAdminForm(forms.ModelForm):
    class Meta:
        model = Perfume
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['top_notes'].queryset = OlfactoryNote.objects.all()
        self.fields['middle_notes'].queryset = OlfactoryNote.objects.all()
        self.fields['base_notes'].queryset = OlfactoryNote.objects.all()
        
        self.fields['category'].queryset = Category.objects.all()
        self.fields['category'].label_from_instance = lambda obj: f"{obj.name} ({obj.parent.name})" if obj.parent else obj.name


class PerfumeCapacityInline(admin.TabularInline):
    model = PerfumeCapacity
    extra = 1


class PerfumeImageInline(admin.TabularInline):
    model = PerfumeImage
    extra = 5


class IngredientInline(admin.TabularInline):
    model = Ingredient
    extra = 1


@admin.register(Capacity)
class CapacityAdmin(admin.ModelAdmin):
    list_display = ('volume',)
    search_fields = ('volume',)


@admin.register(OlfactoryNoteCategory)
class OlfactoryNoteCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(OlfactoryNote)
class OlfactoryNoteAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ('name',)
    list_filter = ('category',)


@admin.register(OlfactoryFamily)
class OlfactoryFamilyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'description')
    inlines = [IngredientInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'show_in_filters', 'show_in_fragrances', 'filter_name', 'description')
    list_editable = ('show_in_filters', 'show_in_fragrances', 'filter_name')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    list_filter = ('parent', 'show_in_filters', 'show_in_fragrances')
    ordering = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'olfactory_family', 'show_in_fragrances')
    list_filter = ('olfactory_family', 'show_in_fragrances')
    search_fields = ('name',)
    list_editable = ('show_in_fragrances',)


@admin.register(Perfume)
class PerfumeAdmin(SortableAdminMixin, admin.ModelAdmin):
    form = PerfumeAdminForm
    list_display = ('name', 'slug', 'category', 'olfactory_family',
                    'available', 'price', 'discount',
                    'show_on_hero', 'show_in_featured', 'show_in_best_sellers',
                    'created_at', 'updated_at', 'order')
    list_editable = ('show_on_hero', 'show_in_featured', 'show_in_best_sellers')
    list_filter = ('available', 'category', 'olfactory_family')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order',)
    inlines = [PerfumeCapacityInline, PerfumeImageInline]
    filter_horizontal = ('top_notes', 'middle_notes', 'base_notes')


@admin.register(PerfumeImage)
class PerfumeImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image')
    actions = [compress_selected_images]