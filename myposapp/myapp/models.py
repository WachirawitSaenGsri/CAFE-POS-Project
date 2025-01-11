# models.py
from django.db import models
from django.contrib.auth.models import User
class Store(models.Model):
    name = models.CharField(max_length=100, unique=True)
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="store")  # Owner of the store

    def __str__(self):
        return self.name

class Member(models.Model):
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('employee', 'Employee'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='owner')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="members", null=True, blank=True)  # Associate member with a store

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.user.username}) - {self.role}"

# เพิ่มหมวดหมู่สินค้าเป็น model แยก
class Category(models.Model):
    name = models.CharField(max_length=100)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="categories", null=True, blank=True)

    def __str__(self):
        return self.name
#class Unit(models.Model):
    #name = models.CharField(max_length=100, unique=True)
#class Stock(models.Model):
    #name = models.CharField(max_length=100, unique=True)
    #amount = models.IntegerField(default=0)
    #unit = models.ForeignKey('Unit', on_delete=models.SET_NULL, null=True)
class Product(models.Model):
    product_name = models.CharField(max_length=100)
    img_product = models.ImageField(upload_to='img/', null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)  # เชื่อมโยงกับหมวดหมู่
    stock = models.IntegerField(default=0,null=True,blank=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="products", null=True, blank=True)  # Associate product with store

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
    customer_name = models.CharField(max_length=100,null=True,blank=True)
    customer_phone = models.CharField(max_length=20,null=True,blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Pending')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="orders", null=True, blank=True)

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
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="payments", null=True, blank=True)

    def __str__(self):
        return f"Payment for Order #{self.order.id} - {self.payment_status}"

class customerMember(models.Model):
    name = models.CharField(max_length=100)  # ชื่อลูกค้า
    email = models.EmailField(unique=True)  # อีเมลของลูกค้า
    phone = models.CharField(max_length=20, unique=True)  # เบอร์โทรศัพท์ของลูกค้า
    points = models.PositiveIntegerField(default=0)  # จำนวนแต้มสะสมของลูกค้า
    created_at = models.DateTimeField(auto_now_add=True)  # วันที่ลงทะเบียนลูกค้า
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="customerMembers", null=True, blank=True)

    def __str__(self):
        # แสดงชื่อและเบอร์โทรของลูกค้าในรูปแบบข้อความ
        return f"{self.name} ({self.phone})"
class PointsConfig(models.Model):
    points_per_baht = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="pointsconfigs", null=True, blank=True)

    def __str__(self):
        return f"Points per Baht: {self.points_per_baht}"
