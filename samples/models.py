from django.db import models
from django.utils.text import slugify
from django.urls import reverse

class Sample(models.Model):
    name = models.CharField(max_length=255, verbose_name="Sample name")
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name="URL")
    image = models.ImageField(upload_to='samples/%Y/%m/%d', verbose_name="Sample image")
    available = models.BooleanField(default=True, verbose_name="Available")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created date")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Update date")

    class Meta:
        verbose_name = "Sample"
        verbose_name_plural = "Samples"
        ordering = ['name']


    def __str__(self):
        return self.name


    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    