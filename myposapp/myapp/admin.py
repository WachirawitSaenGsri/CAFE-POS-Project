# admin.py
from django.contrib import admin
from .models import Product, Member

admin.site.register(Product)
admin.site.register(Member)

