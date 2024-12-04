# myapp/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout , authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from myapp.models import Member,Product,Order, OrderDetail
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from .models import Product
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth.hashers import make_password, check_password
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator
from .forms import *
from django.db import transaction
def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        # ใช้ Django Auth ในการตรวจสอบ username และ password
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
    return render(request, 'login.html')

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
            if not User.objects.filter(username=username).exists():
                if not User.objects.filter(email=email).exists():  # ตรวจสอบว่ามีอีเมลซ้ำหรือไม่
                    user = User.objects.create_user(username=username, email=email, password=password)
                    Member.objects.create(user=user, extra_info="Default info")
                    messages.success(request, 'การลงทะเบียนสำเร็จ! กรุณาเข้าสู่ระบบ.')
                    return redirect('login')
                else:
                    messages.error(request, 'อีเมลนี้ถูกใช้งานแล้ว')
            else:
                messages.error(request, 'ชื่อผู้ใช้นี้ถูกใช้งานแล้ว')
        else:
            messages.error(request, 'รหัสผ่านไม่ตรงกัน')
    return render(request, 'register.html')



def forgot_password(request):
    if request.method == 'POST':
        email = request.POST['email']
        users = User.objects.filter(email=email)

        if users.exists():
            # Redirect to second step: password reset page
            return render(request, 'forgot_password2.html', {'email': email})
        else:
            messages.error(request, 'ไม่พบบัญชีที่ใช้ที่อยู่อีเมลนี้')
            return redirect('forgot_password')

    return render(request, 'forgot_password.html')
@csrf_protect
def reset_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, 'รหัสผ่านไม่ตรงกัน โปรดลองอีกครั้ง')
            return render(request, 'forgot_password2.html', {'email': email})

        if len(new_password) < 8:
            messages.error(request, 'รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร')
            return render(request, 'forgot_password2.html', {'email': email})

        if not any(char.isdigit() for char in new_password):
            messages.error(request, 'รหัสผ่านต้องมีอย่างน้อยหนึ่งตัวเลข')
            return render(request, 'forgot_password2.html', {'email': email})

        if not any(char.isalpha() for char in new_password):
            messages.error(request, 'รหัสผ่านต้องมีตัวอักษรอย่างน้อยหนึ่งตัว')
            return render(request, 'forgot_password2.html', {'email': email})

        try:
            user = User.objects.get(email=email)
            user.password = make_password(new_password)
            user.save()
            messages.success(request, 'รหัสผ่านของคุณถูกรีเซ็ตเรียบร้อยแล้ว! กรุณาเข้าสู่ระบบ.')
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'ไม่พบบัญชีที่ใช้ที่อยู่อีเมลนี้')
            return redirect('forgot_password')

    return redirect('forgot_password')

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
    page_number = request.GET.get('page', 1)

    paginator = Paginator(products, 12)  # แบ่งสินค้าเป็นหน้าละ 12 รายการ
    page_obj = paginator.get_page(page_number)

    form = ProductForm()  # ฟอร์มสำหรับการเพิ่มสินค้า

    return render(request, 'Addmenu.html', {'products': page_obj, 'form': form})

@login_required
def home(request):
    query = request.GET.get('q', '')  # รับค่าคำค้นหา
    category = request.GET.get('category', 'all')  # รับหมวดหมู่
    page_number = request.GET.get('page', 1)  # รับหมายเลขหน้า

    # ดึงหมวดหมู่ทั้งหมดที่มีอยู่ในฐานข้อมูล
    categories = Product.objects.values('category').distinct()  # ดึงหมวดหมู่ทั้งหมดจากฐานข้อมูล

    # ดึงสินค้าทั้งหมด
    products = Product.objects.all()

    # กรองสินค้าตามคำค้นหา (query)
    if query:
        products = products.filter(Q(product_name__icontains=query) | Q(description__icontains=query))

    # กรองสินค้าตามหมวดหมู่
    if category != 'all':
        products = products.filter(category__iexact=category)

    # แบ่งสินค้าเป็นหน้าละ 10 รายการ
    paginator = Paginator(products, 10)
    page_obj = paginator.get_page(page_number)

    # ดึงคำสั่งซื้อที่ยังไม่สมบูรณ์ล่าสุด
    order = Order.objects.filter(customer_name='GOT').last()

    total_price = 0
    total_quantity = 0
    if order:
        total_price = sum(detail.price for detail in order.order_details.all())
        total_quantity = sum(detail.quantity for detail in order.order_details.all())

    # ฟอร์มสำหรับกรอกข้อมูลลูกค้า
    form = CustomerInfoForm()

    return render(request, 'home.html', {
        'page_obj': page_obj,
        'query': query,
        'category': category,
        'categories': categories,  # ส่งหมวดหมู่ทั้งหมด
        'order': order,
        'total_price': total_price,
        'total_quantity': total_quantity,
        'form': form  # ส่งฟอร์มข้อมูลลูกค้า
    })

# Add product to order
@csrf_exempt
def add_to_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            options = data.get('options', '')  # รับค่า options จาก frontend เช่น "SUGAR,FOAM,HOT"
            quantity = data.get('quantity', 1)

            # ตรวจสอบว่ามีสินค้าที่ส่งมาจาก request หรือไม่
            product = Product.objects.get(id=product_id)

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
                existing_options = set(order_detail.options.split(',')) if order_detail.options else set()
                new_options = set(options.split(','))
                combined_options = ', '.join(existing_options.union(new_options))
                order_detail.options = combined_options
                order_detail.price = order_detail.quantity * product.price
                order_detail.save()

            # คำนวณราคาใหม่ของคำสั่งซื้อ
            order.total_price = sum(item.price for item in order.order_details.all())
            order.save()

            return JsonResponse({'status': 'success', 'message': 'Added to order successfully'})
        except Product.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Product not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'invalid method'})

@login_required
@csrf_exempt
def update_order_detail(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_detail_id = data.get('order_detail_id')
            quantity = int(data.get('quantity', 1))

            # ตรวจสอบว่ามี OrderDetail ที่ตรงกับ ID นี้
            order_detail = get_object_or_404(OrderDetail, id=order_detail_id)
            order_detail.quantity = quantity
            order_detail.price = order_detail.product.price * quantity
            order_detail.save()

            # คำนวณราคาใหม่ของคำสั่งซื้อ
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
            data = json.loads(request.body)
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


@login_required
@transaction.atomic
def PayNow(request):
    if request.method == 'POST':
        # Get the customer info from the form
        form = CustomerInfoForm(request.POST)

        if form.is_valid():
            customer_name = form.cleaned_data['customer_name']
            customer_phone = form.cleaned_data['customer_phone']

            # Get the latest order or create a new one
            order = Order.objects.filter(
                customer_name='GOT').last()  # Temporary identifier (replace 'GOT' with actual session or user data)

            if order:
                # Update the order with customer info
                order.customer_name = customer_name
                order.customer_phone = customer_phone
                order.save()

                # Display a success message
                messages.success(request, 'ข้อมูลลูกค้าถูกบันทึกเรียบร้อยแล้ว!')
            else:
                messages.error(request, 'ไม่พบคำสั่งซื้อในระบบ! กรุณาลองใหม่.')

            # Redirect back to the home page (or wherever you want)
            return redirect('home')
        else:
            # If form is not valid, show errors
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วนและถูกต้อง.')

    # If the method is not POST, just render the page (for any errors or initial load)
    return redirect('home')

@login_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)  # รับข้อมูลจากฟอร์มและไฟล์
        if form.is_valid():
            form.save()  # บันทึกข้อมูลสินค้าใหม่ลงฐานข้อมูล
            messages.success(request, 'Product added successfully!')
            return redirect('addmenu')  # เมื่อเพิ่มสินค้าเสร็จแล้ว ให้กลับไปยังหน้า Addmenu
    else:
        form = ProductForm()

    return render(request, 'Addmenu.html', {'form': form})
# View สำหรับการแก้ไขสินค้า
@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product.product_name = request.POST['product_name']
        product.description = request.POST['description']
        product.price = request.POST['price']
        product.category = request.POST['category']

        img_product = request.FILES.get('img_product')
        if img_product:
            product.img_product = img_product

        product.save()
        messages.success(request, 'Product updated successfully!')
        return redirect('addmenu')

    return render(request, 'component/edit_product.html', {'product': product})
# View สำหรับการลบสินค้า
@login_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, 'Product deleted successfully!')
    return redirect('addmenu')


@csrf_exempt
@login_required
def add_category(request):
    if request.method == 'POST':
        category_name = request.POST.get('category_name')

        if category_name:
            # เช็คว่าหมวดหมู่นี้มีอยู่แล้วหรือไม่
            if not Product.objects.filter(category=category_name).exists():
                # เพิ่มหมวดหมู่ใหม่
                # สามารถใช้ Product หรือสร้าง Model แยก Category ตามต้องการ
                Product.objects.create(category=category_name)
                return JsonResponse({'status': 'success', 'message': 'Category added successfully'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Category already exists'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Category name is required'})
    return JsonResponse({'status': 'invalid method'})