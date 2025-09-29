from django.db import models
from django.utils.text import slugify
from django.urls import reverse


class Gift(models.Model):
    name = models.CharField(max_length=255, verbose_name="Name")
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name="URL")
    description = models.TextField(verbose_name="Description")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price")
    image = models.ImageField(upload_to='gifts/%Y/%m/%d', verbose_name="Image")
    available = models.BooleanField(default=True, verbose_name="Available")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created date")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated date")


    class Meta:
        verbose_name = "Gift Wrap"
        verbose_name_plural = "Gift Wraps"
        ordering = ['name']


    def __str__(self):
        return self.name


    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


    def get_absolute_url(self):
        return reverse('gifts:gift_detail', args=[self.slug])
    