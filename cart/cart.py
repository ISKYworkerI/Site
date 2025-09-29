from django.conf import settings
from main.models import Perfume, Capacity
from decimal import Decimal
from main.models import Perfume, PerfumeCapacity, Capacity


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {
                'products': {},
                'samples': [],
                'gift_wrap': None,
                'special_instructions': ''
            }
        self.cart = cart


    def add(self, perfume, capacity, quantity=1, override_quantity=False):
        key = f"{perfume.id}_{capacity.id}"
        if key not in self.cart['products']:
            self.cart['products'][key] = {
                'quantity': 0,
                'perfume_id': perfume.id,
                'capacity_id': capacity.id,
                'price': str(self._get_price(perfume, capacity))
            }
        
        if override_quantity:
            self.cart['products'][key]['quantity'] = quantity
        else:
            self.cart['products'][key]['quantity'] = max(1, self.cart['products'][key]['quantity'] + quantity)
        
        self.save()


    def _get_price(self, perfume, capacity):
        try:
            perfume_capacity = PerfumeCapacity.objects.get(perfume=perfume, capacity=capacity)
            return perfume_capacity.price if perfume_capacity.price else perfume.get_price_with_discount()
        except PerfumeCapacity.DoesNotExist:
            return perfume.get_price_with_discount()


    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True


    def remove(self, perfume, capacity):
        key = f"{perfume.id}_{capacity.id}"
        if key in self.cart['products']:
            del self.cart['products'][key]
            self.save()


    def get_total_price(self):
        total = Decimal(0)
        for item in self:
            total += Decimal(item['price']) * item['quantity']
        return total


    def __iter__(self):
        for key, item_data in self.cart['products'].items():
            try:
                perfume = Perfume.objects.get(id=item_data['perfume_id'])
                capacity = Capacity.objects.get(id=item_data['capacity_id'])
                yield {
                    'key': key,
                    'perfume': perfume,
                    'capacity': capacity,
                    'quantity': item_data['quantity'],
                    'price': Decimal(item_data['price']),
                    'total_price': Decimal(item_data['price']) * item_data['quantity'],
                    'type': 'product',
                }
            except (Perfume.DoesNotExist, Capacity.DoesNotExist):
                continue

        from samples.models import Sample
        for sample_id in self.cart['samples']:
            try:
                sample = Sample.objects.get(id=sample_id)
                yield {
                    'key': f"sample_{sample_id}",
                    'sample': sample,
                    'quantity': 1,
                    'price': Decimal(0),
                    'total_price': Decimal(0),
                    'type': 'sample',
                }
            except Sample.DoesNotExist:
                continue

        from gifts.models import Gift
        if self.cart['gift_wrap']:
            try:
                gift = Gift.objects.get(id=self.cart['gift_wrap'])
                yield {
                    'key': f"gift_{self.cart['gift_wrap']}",
                    'gift': gift,
                    'quantity': 1,
                    'price': Decimal(gift.price),
                    'total_price': Decimal(gift.price),
                    'type': 'gift',
                }
            except Gift.DoesNotExist:
                pass


    def __len__(self):
        return sum(item['quantity'] for item in self.cart['products'].values())


    def clear(self):
        self.cart = {
            'products': {},
            'samples': [],
            'gift_wrap': None,
            'special_instructions': ''
        }
        self.save()
    

    def update_quantity(self, perfume, capacity, quantity):
        key = f"{perfume.id}_{capacity.id}"
        if key in self.cart['products']:  
            self.cart['products'][key]['quantity'] = quantity
            self.save()


    def add_sample(self, sample_id):
        sample_id = str(sample_id)  
        if sample_id not in self.cart['samples'] and len(self.cart['samples']) < 2:
            self.cart['samples'].append(sample_id)
            self.save()


    def replace_sample(self, sample_id):
        sample_id = str(sample_id)
        if sample_id not in self.cart['samples']:
            if len(self.cart['samples']) >= 2:
                self.cart['samples'].pop(0)  # Удаляем первый пробник
            self.cart['samples'].append(sample_id)
            self.save()


    def remove_sample(self, sample_id):
        sample_id = str(sample_id)  
        if sample_id in self.cart['samples']:
            self.cart['samples'].remove(sample_id)
            self.save()


    def remove_all_samples(self):
        self.cart['samples'] = []
        self.save()


    def set_gift_wrap(self, gift_id):
        self.cart['gift_wrap'] = gift_id
        self.save()


    def remove_gift_wrap(self):
        self.cart['gift_wrap'] = None
        self.save()


    def set_special_instructions(self, instructions):
        self.cart['special_instructions'] = instructions
        self.save()


    def get_samples(self):
        from samples.models import Sample
        return Sample.objects.filter(id__in=self.cart['samples'])


    def get_gift_wrap(self):
        from gifts.models import Gift
        if self.cart['gift_wrap']:
            try:
                return Gift.objects.get(id=self.cart['gift_wrap'])
            except Gift.DoesNotExist:
                return None
        return None