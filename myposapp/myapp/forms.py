# myapp/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import *

class CustomerInfoForm(forms.Form):
    customer_name = forms.CharField(max_length=100, label='Customer Name')
    customer_phone = forms.CharField(max_length=15, label='Customer Phone')

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['product_name', 'img_product', 'description', 'price', 'category']
        category = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        # ดึงข้อมูล category ทั้งหมดจากฐานข้อมูลมาเป็น choices
        self.fields['category'].choices = [(cat, cat) for cat in Product.objects.values_list('category', flat=True).distinct()]