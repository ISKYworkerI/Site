from .models import Category, OlfactoryFamily, Ingredient, Perfume
from django.shortcuts import render
from django.db.models import Q
from django.core.cache import cache


def fragrance_menu(request):
    return {
        'fragrance_categories': Category.objects.filter(show_in_fragrances=True),
        'olfactory_families': OlfactoryFamily.objects.all(),
        'fragrance_ingredients': Ingredient.objects.filter(show_in_fragrances=True),
    }

def navigation_categories(request):
    cache_key = 'navigation_categories'
    categories = cache.get(cache_key)
    if not categories:
        categories = Category.objects.all()[:3]
        cache.set(cache_key, categories, 60 * 60)  
    return {'navigation_categories': categories}


def search_results(request):
    query = request.GET.get('q', '').strip()
    context = {
        'query': query,
        'results': [],
        'categories': [],
        'olfactory_families': [],
        'ingredients': [],
    }

    if query:
        # Search for perfumes
        context['results'] = Perfume.objects.filter(
            Q(name__icontains=query) & Q(available=True)
        ).distinct()[:10]

        # Search for categories
        context['categories'] = Category.objects.filter(
            Q(name__icontains=query) & Q(show_in_fragrances=True)
        )[:5]

        # Search for olfactory families
        context['olfactory_families'] = OlfactoryFamily.objects.filter(
            Q(name__icontains=query)
        )[:5]

        # Search for ingredients
        context['ingredients'] = Ingredient.objects.filter(
            Q(name__icontains=query) & Q(show_in_fragrances=True)
        )[:5]

    return render(request, 'search/results.html', context)