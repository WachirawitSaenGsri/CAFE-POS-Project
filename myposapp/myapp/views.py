# myapp/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from myapp.models import Member,Product,Order, OrderDetail
from .forms import UserCredentialForm
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from .models import Product
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import json
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
def Order1(request):
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
    products = Product.objects.all()  # ดึงข้อมูลสินค้าทั้งหมดจากฐานข้อมูล
    return render(request, 'Addmenu.html', {'products': products})
    #return render(request, 'Addmenu.html')

@login_required
def home(request):
    query = request.GET.get('q')  # รับค่าคำค้นหา
    category = request.GET.get('category', 'all')  # รับค่า category, ตั้งค่าเริ่มต้นเป็น 'all'

    # เริ่มจากดึงสินค้าทั้งหมด
    products = Product.objects.all()

    # ถ้ามีการค้นหา ให้กรองข้อมูลด้วยคำค้นหา
    if query:
        products = products.filter(Q(product_name__icontains=query) | Q(description__icontains=query))

    # กรองข้อมูลตามหมวดหมู่ที่เลือก (ยกเว้น 'all' ซึ่งหมายถึงทุกหมวดหมู่)
    if category != 'all':
        products = products.filter(category__iexact=category)

    # ดึงคำสั่งซื้อล่าสุดที่ยังไม่สมบูรณ์
    order = Order.objects.filter(customer_name='GOT').last()

    # ตรวจสอบว่ามีคำสั่งซื้ออยู่หรือไม่
    total_price = 0
    total_quantity = 0
    if order:
        # คำนวณจำนวนรวมและราคารวม
        total_price = sum(detail.price for detail in order.order_details.all())
        total_quantity = sum(detail.quantity for detail in order.order_details.all())

    return render(request, 'home.html', {
        'products': products,
        'query': query,
        'category': category,
        'order': order,  # ส่งคำสั่งซื้อ (order) ไปยังเทมเพลต
        'total_price': total_price,  # ส่งราคารวมไปยังเทมเพลต
        'total_quantity': total_quantity  # ส่งจำนวนรวมไปยังเทมเพลต
    })

@csrf_exempt
def add_to_order(request):
    if request.method == 'POST':
        try:
            # รับข้อมูล JSON จาก Frontend
            data = json.loads(request.body)
            product_id = data.get('product_id')
            options = data.get('options', '')  # รับค่า options จาก frontend เช่น "ESPRESSO,SUGAR,HOT"
            quantity = data.get('quantity', 1)

            print(f"Product ID: {product_id}, Options: {options}, Quantity: {quantity}")  # ตรวจสอบข้อมูลที่ได้รับ

            # ตรวจสอบว่ามีสินค้าที่ส่งมาจาก request หรือไม่
            product = Product.objects.get(id=product_id)

            # ลบเงื่อนไขการตรวจสอบ options เพื่ออนุญาตให้สามารถเพิ่มสินค้าได้แม้ options จะว่าง
            # ตรวจสอบว่ามี Order ที่ยังไม่ได้ปิดหรือไม่
            order, created = Order.objects.get_or_create(
                customer_name='GOT',  # ใช้ข้อมูลชั่วคราวก่อน
                customer_phone='090-000-0000',
                defaults={'total_price': 0}
            )

            # เพิ่มสินค้าใน OrderDetail หรืออัปเดตรายการเดิม
            order_detail, created = OrderDetail.objects.get_or_create(
                order=order,
                product=product,
                defaults={'quantity': quantity, 'price': product.price * quantity, 'options': options}
            )

            if not created:  # ถ้ามีอยู่แล้ว ให้ปรับจำนวนและ options
                order_detail.quantity += quantity
                # เพิ่ม options เข้าไปในรายการเดิมโดยไม่ซ้ำกัน
                existing_options = set(order_detail.options.split(',')) if order_detail.options else set()
                new_options = set(options.split(','))
                combined_options = ', '.join(existing_options.union(new_options))
                order_detail.options = combined_options  # อัปเดต options ใหม่
                order_detail.price = order_detail.quantity * product.price
                order_detail.save()

            print(f"Order Detail Updated: {order_detail}")  # ตรวจสอบว่า OrderDetail ถูกอัปเดตหรือไม่

            # คำนวณราคาใหม่ของคำสั่งซื้อ
            order.total_price = sum(item.price for item in order.order_details.all())
            order.save()

            return JsonResponse({'status': 'success', 'message': 'Added to order successfully'})
        except Product.DoesNotExist:
            print('Product not found')  # เพิ่มข้อความสำหรับการดีบัก
            return JsonResponse({'status': 'error', 'message': 'Product not found'})
        except Exception as e:
            print(f"Error: {str(e)}")  # แสดงข้อความ Error
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'invalid method'})
@login_required
@csrf_exempt
def update_order_detail(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)  # รับข้อมูล JSON จาก request body
            order_detail_id = data.get('order_detail_id')
            quantity = int(data.get('quantity', 1))

            # ตรวจสอบว่ามี OrderDetail ที่สอดคล้องกับ ID นี้หรือไม่
            order_detail = get_object_or_404(OrderDetail, id=order_detail_id)
            order_detail.quantity = quantity
            order_detail.price = order_detail.product.price * quantity
            order_detail.save()

            # อัปเดตราคาทั้งหมดของคำสั่งซื้อ
            order_detail.order.total_price = sum([item.price for item in order_detail.order.order_details.all()])
            order_detail.order.save()

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'invalid method'})


@login_required
@csrf_exempt
def delete_order_detail(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)  # รับข้อมูล JSON จาก request body
            order_detail_id = data.get('order_detail_id')

            # ตรวจสอบว่า OrderDetail นี้มีอยู่ในระบบหรือไม่
            order_detail = get_object_or_404(OrderDetail, id=order_detail_id)
            order_detail.delete()

            # อัปเดตราคาทั้งหมดของคำสั่งซื้อ
            order_detail.order.total_price = sum([item.price for item in order_detail.order.order_details.all()])
            order_detail.order.save()

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'invalid method'})