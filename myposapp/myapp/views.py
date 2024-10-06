# myapp/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from myapp.models import Member,Product
from .forms import UserCredentialForm
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from .models import Product

def user_login(request):
    # ตรวจสอบว่ามีการส่งข้อมูลเข้ามาหรือไม่
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        # ตรวจสอบ username และ password จากตาราง Member
        try:
            member = Member.objects.get(username=username, password=password)
            if member:
                # สร้างผู้ใช้ชั่วคราวใน Django Auth เพื่อเข้าสู่ระบบ
                user, created = User.objects.get_or_create(username=member.username)
                login(request, user)
                return redirect('home')  # ถ้า login สำเร็จจะ redirect ไปหน้า home
            else:
                messages.error(request, 'Username หรือ Password ไม่ถูกต้อง')
        except Member.DoesNotExist:
            messages.error(request, 'Username หรือ Password ไม่ถูกต้อง')
    return render(request, 'login.html')  # ถ้าเป็น GET จะให้แสดงหน้า login

def user_logout(request):
    logout(request)
    return redirect('login')  # เมื่อ logout แล้วให้กลับไปหน้า login

@login_required
def home(request):
    return render(request, 'home.html')  # หน้า home หลังจาก login สำเร็จ

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Member  # นำเข้า Member model

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:
            # ตรวจสอบว่า username นี้มีอยู่ในระบบแล้วหรือไม่
            if not User.objects.filter(username=username).exists():
                # สร้างผู้ใช้ใหม่ใน User model
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()

                # บันทึกข้อมูลผู้ใช้ลงใน Member model ด้วย
                member = Member(username=username, password=password)
                member.save()

                # แสดงข้อความแจ้งเตือนความสำเร็จในการสมัครสมาชิก
                messages.success(request, 'สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบด้วยบัญชีผู้ใช้ของคุณ')
                return redirect('login')  # เปลี่ยนเป็นการ redirect ไปหน้า login แทน
            else:
                messages.error(request, 'Username นี้มีอยู่แล้ว')
        else:
            messages.error(request, 'รหัสผ่านไม่ตรงกัน')
    return render(request, 'register.html')

@login_required
def Menu(request):
    products = Product.objects.all()  # ดึงข้อมูลสินค้าทั้งหมดจากฐานข้อมูล
    return render(request, 'home.html', {'products': products})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # ตัวอย่างการจัดการสินค้าในตะกร้า (คุณสามารถปรับเปลี่ยนตามโครงสร้างที่คุณใช้จริง)
    cart = request.session.get('cart', [])
    cart.append({'product_id': product.id, 'product_name': product.product_name, 'price': float(product.price)})
    request.session['cart'] = cart

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))  # กลับไปหน้าก่อนหน้า


@login_required
def Order(request):
    return render(request, 'Order.html')

@login_required
def PayMent(request):
    return render(request, 'Payment.html')

@login_required
def Marketing(request):
    return render(request, 'Marketing.html')

@login_required
def inventory(request):
    return render(request, 'inventory.html')

@login_required
def History_Order(request):
    return render(request, 'History_Order.html')

@login_required
def Member1(request):
    return render(request, 'Member1.html')

@login_required
def Addmenu(request):
    return render(request, 'Addmenu.html')