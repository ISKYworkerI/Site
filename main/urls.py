from django.urls import path
from .views import CatalogView, PerfumeDetailView, HomeView, about
from .context_processors import search_results

app_name = 'main'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('catalog/', CatalogView.as_view(), name='catalog'),
    path('perfume/<slug:slug>/', PerfumeDetailView.as_view(), name='perfume_detail'),
    path('about/', about, name='about'),
    path('results/', search_results, name='results'),
]
