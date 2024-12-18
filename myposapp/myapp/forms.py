# myapp/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import *

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label="Enter your email address")

class PasswordResetForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput, label="New Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data
class CustomerInfoForm(forms.Form):
    customer_name = forms.CharField(max_length=100, label='Customer Name')
    customer_phone = forms.CharField(max_length=15, label='Customer Phone')


class OptionForm(forms.ModelForm):
    class Meta:
        model = Option
        fields = ['name', 'price']

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return price


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['product_name', 'description', 'price', 'category', 'img_product', 'stock']

    stock = forms.IntegerField(initial=0, required=False)
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=True)

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()  # Dynamically load categories


class PaymentForm(forms.Form):
    payment_method = forms.ChoiceField(
        choices=[('cash', 'Cash'), ('Promptpay', 'Promptpay')],
        label="Payment Method",
        widget=forms.RadioSelect
    )