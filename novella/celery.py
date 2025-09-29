import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'novella.settings')

app = Celery('novella')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()