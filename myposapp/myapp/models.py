# models.py
from django.db import models

class Member(models.Model):
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=50)

    def __str__(self):
        return self.username

class Product(models.Model):
    product_name = models.CharField(max_length=100)  # ชื่อสินค้า
    img_product = models.ImageField(upload_to='img/', null=True, blank=True)  # รูปสินค้า
    description = models.TextField(null=True, blank=True)  # คำอธิบาย
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # ราคา
    order_id = models.IntegerField(null=True)  # รหัสการสั่งซื้อ
    number = models.CharField(max_length=20)  # เบอร์โทรศัพท์ลูกค้า
    name_customer = models.CharField(max_length=50)  # ชื่อลูกค้า

    def __str__(self):
        return self.product_name

