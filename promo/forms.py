from django import forms


class PromoCodeForm(forms.Form):
    code = forms.CharField(max_length=20, label='Промокод')
    