# admin.py
from django.contrib import admin
from .models import *

admin.site.register(Product)
admin.site.register(Member)
admin.site.register(Order)
admin.site.register(OrderDetail)


