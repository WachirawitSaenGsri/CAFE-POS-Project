# models.py
from decimal import Decimal
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.db import transaction
class Store(models.Model):
    name = models.CharField(max_length=100, unique=True)
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="store")  # เจ้าของร้าน

    def __str__(self):
        return self.name

class Member(models.Model):
    ROLE_CHOICES = (
        ('owner', 'เจ้าของร้าน'),
        ('employee', 'พนักงาน'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='owner')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="members", null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.user.username}) - {self.role}"
    def get_role_display_name(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)

# เพิ่มหมวดหมู่สินค้าเป็น model แยก
class Category(models.Model):
    name = models.CharField(max_length=100)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="categories", null=True, blank=True)

    def __str__(self):
        return self.name

class Ingredient(models.Model):
    name = models.CharField(max_length=100)  # ชื่อวัตถุดิบ
    unit = models.CharField(max_length=50)  # หน่วย เช่น กรัม, ลิตร
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # ปริมาณวัตถุดิบในสต็อก
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=10)  # ปริมาณที่ควรเติมเมื่อวัตถุดิบเหลือน้อย
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="ingredients", null=True, blank=True)

    def __str__(self):
        return self.name

class Promotion(models.Model):
    name = models.CharField(max_length=100)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="promotions", null=True, blank=True)

    def __str__(self):
        return self.name

    def is_active(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date
class Product(models.Model):
    product_name = models.CharField(max_length=100)
    img_product = models.ImageField(upload_to='img/', null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)  # เชื่อมโยงกับหมวดหมู่
    #stock = models.IntegerField(default=0,null=True,blank=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="products", null=True, blank=True)
    ingredients = models.ManyToManyField(Ingredient, through='ProductIngredient')  # เชื่อมโยงกับวัตถุดิบ
    promotion = models.ForeignKey(Promotion, null=True, blank=True, on_delete=models.SET_NULL)

    def get_discounted_price(self):
        if self.promotion and self.promotion.is_active():
            discount = self.price * (self.promotion.discount_percentage / 100)
            return self.price - discount
        return self.price

    def __str__(self):
        return self.product_name
    def is_low_stock(self):
        for ingredient in self.ingredients.all():
            if ingredient.stock < ingredient.reorder_level:
                return True
        return False

class ProductIngredient(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)  # จำนวนที่ใช้ในแต่ละผลิตภัณฑ์
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="productingredients", null=True, blank=True)

    def __str__(self):
        return f"{self.product.product_name} uses {self.quantity} {self.ingredient.unit} of {self.ingredient.name}"

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
    products = models.ManyToManyField(Product)
    employee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="handled_orders")
    points_used = models.IntegerField(default=0)
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

    def __str__(self):
        return f"{self.product.product_name} (x{self.quantity})"
    def total_price(self):
        return self.price

class OrderDetailOption(models.Model):
    order_detail = models.ForeignKey(OrderDetail, on_delete=models.CASCADE, related_name="order_detail_options")
    option = models.ForeignKey(Option, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.order_detail} - {self.option.name} (x{self.quantity})"
    def total_price(self):
        return self.option.price * self.quantity
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
    points_per_baht = models.DecimalField(max_digits=5, decimal_places=2, default=1.00) # กำหนดแต้มที่ได้รับต่อ 1 บาท
    points_to_baht = models.DecimalField(max_digits=5, decimal_places=2,default=10.00)  # กำหนดแต้มที่สามารถแลกเป็นกี่บาท บาท
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="pointsconfigs", null=True, blank=True)

    def __str__(self):
        return f"Points per Baht: {self.points_per_baht}, Points to Baht: {self.points_to_baht}"
