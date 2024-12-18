# models.py
from django.db import models
from django.contrib.auth.models import User

class Member(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('unknown', 'Unknown'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='unknown')

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.user.username}) - {self.role}"

# เพิ่มหมวดหมู่สินค้าเป็น model แยก
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    product_name = models.CharField(max_length=100)
    img_product = models.ImageField(upload_to='img/', null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)  # เชื่อมโยงกับหมวดหมู่
    stock = models.IntegerField(default=0,null=True,blank=True)

    def __str__(self):
        return self.product_name

    def is_low_stock(self):
        return self.stock <= 5

class Option(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='options')  # เชื่อมโยงกับ Product
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.name} (+{self.price} ฿)"

class Order(models.Model):
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id}"

    def update_total_price(self):
        self.total_price = sum([item.price for item in self.order_details.all()])
        self.save()

class OrderDetail(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_details')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    options = models.ManyToManyField(Option, blank=True)

    def __str__(self):
        return f"{self.product.product_name} (x{self.quantity})"

class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)  # e.g.,  "cash"
    payment_status = models.CharField(max_length=20, default="Pending")  # e.g., "Success", "Failed"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Order #{self.order.id} - {self.payment_status}"

