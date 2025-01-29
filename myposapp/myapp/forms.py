# myapp/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import *

class EmployeeForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    role = forms.ChoiceField(choices=Member.ROLE_CHOICES)
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password', 'role']
class PromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = ['name', 'discount_percentage', 'start_date', 'end_date']
class IngredientOrderForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'stock', 'unit', 'reorder_level']

class ProductIngredientForm(forms.ModelForm):
    class Meta:
        model = ProductIngredient
        fields = ['product', 'ingredient', 'quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 0, 'step': 'any'})  # จำกัดให้กรอกแค่ตัวเลข
        }

class CustomerMemberForm(forms.ModelForm):
    class Meta:
        model = customerMember
        fields = ['name', 'email', 'phone', 'points']  # ฟิลด์ที่ต้องการให้กรอก
        widgets = {
            'points': forms.NumberInput(attrs={'min': 0}),
        }
class PointsConfigForm(forms.ModelForm):
    class Meta:
        model = PointsConfig
        fields = ['points_per_baht']
class CustomerInfoForm(forms.Form):
    customer_name = forms.CharField(max_length=100, label='Customer Name', required=False)
    customer_phone = forms.CharField(max_length=15, label='Customer Phone', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
    amount_paid = forms.DecimalField(
        max_digits=10, decimal_places=2,
        label="Amount Paid",
        min_value=0,
        required=True
    )

