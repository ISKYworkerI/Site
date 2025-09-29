from django.views.generic import ListView, DetailView
from .models import Perfume, Category, Capacity, PerfumeCapacity, \
      OlfactoryNote, OlfactoryFamily, Ingredient
from django.shortcuts import render
from django.db.models import Q


class CatalogView(ListView):
    model = Perfume
    template_name = 'main/product/catalog.html'
    context_object_name = 'perfumes'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(available=True).order_by('order')

        category_slugs = self.request.GET.getlist('category')
        capacity_volumes = self.request.GET.getlist('capacity')
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        sort = self.request.GET.get('sort')
        search_query = self.request.GET.get('search', '')
        olfactory_family = self.request.GET.get('olfactory_family')
        ingredient_id = self.request.GET.get('ingredient')

        if category_slugs:
            subcategory_slugs = Category.objects.filter(parent__slug__in=category_slugs).values_list('slug', flat=True)
            category_slugs.extend(subcategory_slugs)
            queryset = queryset.filter(category__slug__in=category_slugs)
        else:
            queryset = queryset.all()

        if capacity_volumes:
            queryset = queryset.filter(
                Q(capacities__volume__in=capacity_volumes) & Q(capacities__perfumecapacity__available=True)
            ).distinct()

        if min_price:
            queryset = queryset.filter(price__gte=min_price)

        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        if olfactory_family:
            queryset = queryset.filter(olfactory_family__id=olfactory_family)

        if ingredient_id:
            try:
                ingredient = Ingredient.objects.get(id=ingredient_id)
                queryset = queryset.filter(olfactory_family=ingredient.olfactory_family)
            except Ingredient.DoesNotExist:
                queryset = queryset.none()

        if sort == 'on_sale':
            queryset = queryset.filter(discount__gt=0)

        if sort == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-price')

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(top_notes__name__icontains=search_query) |
                Q(middle_notes__name__icontains=search_query) |
                Q(base_notes__name__icontains=search_query)
            ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_slugs = self.request.GET.getlist('category')

        # Добавляем выбранную категорию (первую, если выбрано несколько)
        selected_category = None
        if category_slugs:
            try:
                selected_category = Category.objects.get(slug=category_slugs[0])
            except Category.DoesNotExist:
                selected_category = None

        context['categories'] = Category.objects.filter(parent=None)
        context['capacities'] = Capacity.objects.all()
        context['olfactory_families'] = OlfactoryFamily.objects.all()
        context['selected_categories'] = category_slugs
        context['selected_capacities'] = self.request.GET.getlist('capacity')
        context['selected_olfactory_family'] = self.request.GET.get('olfactory_family')
        context['selected_ingredient'] = self.request.GET.get('ingredient')
        context['selected_category'] = selected_category  # Добавляем выбранную категорию

        return context


class HomeView(ListView):
    model = Perfume
    template_name = 'main/index.html'
    context_object_name = 'perfumes'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        hero_product = Perfume.objects.filter(show_on_hero=True).first()
        context['hero_product'] = hero_product
        
        featured_products = Perfume.objects.filter(show_in_featured=True, available=True).order_by('order')
        context['featured_products'] = featured_products
        
        best_sellers = Perfume.objects.filter(show_in_best_sellers=True, available=True).order_by('order')
        context['best_sellers'] = best_sellers
        
        filter_categories = Category.objects.filter(show_in_filters=True)
        context['filter_categories'] = filter_categories
        
        return context


class PerfumeDetailView(DetailView):
    model = Perfume
    template_name = 'main/product/detail.html'
    context_object_name = 'perfume'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        perfume = self.object
        
        if not perfume.available:
            context['is_available'] = False
        else:
            available_capacities = PerfumeCapacity.objects.filter(
                perfume=perfume, 
                available=True
            ).select_related('capacity')
            
            context['available_capacities'] = available_capacities
            context['is_available'] = True
            
            context['top_notes'] = perfume.top_notes.all()
            context['middle_notes'] = perfume.middle_notes.all()
            context['base_notes'] = perfume.base_notes.all()
            
        return context


def about(request):
    return render(request, 'main/about.html')
    