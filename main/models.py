from django.db import models
from .utils.image_utils import compress_image
from django.urls import reverse


class Capacity(models.Model):
    """Модель для объема флакона (например, 50ml, 100ml)"""
    volume = models.CharField(max_length=20, unique=True)
    
    
    def __str__(self):
        return self.volume


class OlfactoryNoteCategory(models.Model):
    """Категория нот (верхние, средние, базовые)"""
    name = models.CharField(max_length=50, unique=True)
    

    def __str__(self):
        return self.name


class OlfactoryNote(models.Model):
    """Ольфакторная нота (например, бергамот, амбра)"""
    name = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(OlfactoryNoteCategory, on_delete=models.CASCADE, 
                                related_name='notes')
    

    def __str__(self):
        return self.name


class OlfactoryFamily(models.Model):
    """Ольфакторная семья (например, Amber Oriental)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    

    def __str__(self):
        return self.name
    

class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)
    olfactory_family = models.ForeignKey(OlfactoryFamily, on_delete=models.CASCADE, 
                                        related_name='ingredients')
    show_in_fragrances = models.BooleanField(default=False, 
                                            verbose_name="Show in Fragrances dropdown")
    

    def __str__(self):
        return self.name


    class Meta:
        verbose_name = 'ingredient'
        verbose_name_plural = 'ingredients'


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              related_name='subcategories')
    show_in_filters = models.BooleanField(default=False, 
                                        verbose_name="Show in filters section")
    show_in_fragrances = models.BooleanField(default=False, 
                                            verbose_name="Show in Fragrances dropdown") 
    filter_name = models.CharField(max_length=50, blank=True, 
                                 verbose_name="Filter name (if different from category)")
    filter_slug = models.SlugField(max_length=50, blank=True, 
                                 verbose_name="Filter slug (for frontend)")
    description = models.TextField(blank=True, verbose_name="Description")


    def __str__(self):
        if self.parent:
            return f"{self.name} ({self.parent.name})"
        return self.name


    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['name'])]
        verbose_name = 'category'
        verbose_name_plural = 'categories'
        

    def get_item_count(self):
        return Perfume.objects.filter(category=self).count()


class Perfume(models.Model):
    """Модель парфюма"""
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    available = models.BooleanField(default=True)
    capacities = models.ManyToManyField(Capacity, through='PerfumeCapacity', 
                                       related_name='perfumes', blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, 
                                related_name='perfumes')
    olfactory_family = models.ForeignKey(OlfactoryFamily, on_delete=models.SET_NULL, 
                                        null=True, blank=True, related_name='perfumes')
    top_notes = models.ManyToManyField(OlfactoryNote, related_name='top_notes', 
                                      limit_choices_to={'category__name': 'Top'}, blank=True)
    middle_notes = models.ManyToManyField(OlfactoryNote, related_name='middle_notes', 
                                         limit_choices_to={'category__name': 'Middle'}, blank=True)
    base_notes = models.ManyToManyField(OlfactoryNote, related_name='base_notes', 
                                       limit_choices_to={'category__name': 'Base'}, blank=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d', blank=True)
    detail_media = models.FileField(upload_to='products/media/%Y/%m/%d', blank=True, 
                                   help_text="Upload an image or video for the detail page")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    story = models.TextField(blank=True, help_text="История создания парфюма")
    order = models.PositiveIntegerField(default=0)
    show_on_hero = models.BooleanField(default=False, 
                                     verbose_name="Show in hero section (plus button)")
    show_in_featured = models.BooleanField(default=False, 
                                         verbose_name="Show in featured products section")
    show_in_best_sellers = models.BooleanField(default=False, 
                                             verbose_name="Show in best sellers section")


    def __str__(self):
        return self.name


    def get_price_with_discount(self):
        if self.discount > 0:
            return round(self.price * (1 - (self.discount / 100)), 2)
        return round(self.price, 2)
    

    def get_absolute_url(self):
        return reverse('main:perfume_detail', args=[self.slug])


class PerfumeCapacity(models.Model):
    """Доступные объемы для парфюма"""
    perfume = models.ForeignKey(Perfume, on_delete=models.CASCADE)
    capacity = models.ForeignKey(Capacity, on_delete=models.CASCADE)
    available = models.BooleanField(default=True)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)


    class Meta:
        unique_together = ('perfume', 'capacity')
        

    def __str__(self):
        return f"{self.perfume.name} - {self.capacity.volume}"


    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.perfume.price
        super().save(*args, **kwargs)


class PerfumeImage(models.Model):
    """Изображения парфюма"""
    product = models.ForeignKey(Perfume, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/%Y/%m/%d', blank=True)
    

    def __str__(self):
        return f'{self.product.name} - {self.image.name}'
    

    def save(self, *args, **kwargs):
        if self.image.size > 5 * 1024 * 1024:  
            self.image = compress_image(self.image)
        super().save(*args, **kwargs)