# admin.py
from django.contrib import admin
from .models import *

admin.site.register(Product)
admin.site.register(Member)
admin.site.register(Order)
admin.site.register(OrderDetail)
admin.site.register(Option)
admin.site.register(Payment)
admin.site.register(Category)
admin.site.register(customerMember)
admin.site.register(PointsConfig)
admin.site.register(Store)
admin.site.register(Ingredient)
admin.site.register(ProductIngredient)

