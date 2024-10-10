# models.py
from django.db import models

class Member(models.Model):
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=50)

    def __str__(self):
        return self.username

class Product(models.Model):
    CATEGORIES = (
        ('coffee', 'Coffee'),
        ('desserts', 'Desserts'),
        ('breakfast', 'Breakfast'),
        ('other', 'Other')
    )
    product_name = models.CharField(max_length=100)
    img_product = models.ImageField(upload_to='img/', null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='other')  # หมวดหมู่

    def __str__(self):
        return self.product_name

class Order(models.Model):
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id}"

class OrderDetail(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_details')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    options = models.TextField()  # เก็บ options เช่น "SUGAR,FOAM,HOT"

    def __str__(self):
        return f"{self.product.product_name} (x{self.quantity})"