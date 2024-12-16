# myapp/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout , authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth.hashers import make_password, check_password
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator
from .forms import *
from django.db import transaction
from myapp.models import Product, Order, OrderDetail, Option, Category, Payment




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
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        firstname = request.POST.get('firstname', '').strip()
        lastname = request.POST.get('lastname', '').strip()

        # ตรวจสอบข้อมูลพื้นฐาน
        if not username or not email or not password or not confirm_password or not firstname or not lastname:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
            return render(request, 'register.html')

        if password != confirm_password:
            messages.error(request, 'รหัสผ่านไม่ตรงกัน')
            return render(request, 'register.html')

        if len(password) < 8:
            messages.error(request, 'รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร')
            return render(request, 'register.html')

        # ตรวจสอบว่า username และ email ไม่ซ้ำ
        if User.objects.filter(username=username).exists():
            messages.error(request, 'ชื่อผู้ใช้นี้ถูกใช้งานแล้ว')
            return render(request, 'register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'อีเมลนี้ถูกใช้งานแล้ว')
            return render(request, 'register.html')

        # สร้าง User และ Member
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.first_name = firstname
            user.last_name = lastname
            user.save()
            Member.objects.create(user=user)
            messages.success(request, 'การลงทะเบียนสำเร็จ! กรุณาเข้าสู่ระบบ.')
            return redirect('login')
        except Exception as e:
            print(f"Error during registration: {e}")
            messages.error(request, 'เกิดข้อผิดพลาดในการลงทะเบียน กรุณาลองใหม่')

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
@transaction.atomic
def PayMent(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Initialize total order price
    total_order_price = 0
    order_details = []

    # Calculate total item price and total order price
    for detail in order.order_details.all():
        total_item_price = detail.quantity * detail.price
        order_details.append({
            'product_name': detail.product.product_name,
            'quantity': detail.quantity,
            'price': detail.price,
            'total_item_price': total_item_price,
            'options': detail.options,  # Include options in the order details
        })
        total_order_price += total_item_price

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment_method = form.cleaned_data['payment_method']
            amount_paid = form.cleaned_data['amount_paid']

            # Simulate payment logic here
            payment = Payment.objects.create(
                order=order,
                amount=amount_paid,
                payment_method=payment_method,
                payment_status="Success"  # Change to dynamic status if integrating payment gateway
            )

            # Calculate change
            change = amount_paid - total_order_price
            if change < 0:
                messages.error(request, f'Insufficient amount. You still owe {-change} ฿')
            else:
                messages.success(request, f'Payment completed successfully! Change: {change} ฿')

            return redirect('History_Order')  # Redirect to order history or confirmation page

    else:
        form = PaymentForm()

    # Pass the calculated values to the template
    return render(request, 'Payment.html', {
        'order': order,
        'form': form,
        'total_order_price': total_order_price,  # Pass the total order price
        'order_details': order_details,  # Pass the detailed order data
    })

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
    search_query = request.GET.get('search', '')  # รับคำค้นหาจากฟอร์ม

    # ถ้าคำค้นหามีการระบุ
    if search_query:
        products = Product.objects.filter(
            Q(product_name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    else:
        # ถ้าไม่มีคำค้นหาก็ให้ดึงสินค้าทั้งหมด
        products = Product.objects.all()

    # การแบ่งหน้า
    page_number = request.GET.get('page', 1)  # รับค่าหน้าจาก query string
    paginator = Paginator(products, 12)  # แบ่งสินค้าเป็นหน้าละ 12 รายการ
    page_obj = paginator.get_page(page_number)

    form = ProductForm()  # ฟอร์มสำหรับการเพิ่มสินค้า

    return render(request, 'Addmenu.html', {'products': page_obj, 'form': form, 'search_query': search_query})

def home(request):
    query = request.GET.get('q', '')  # รับค่าคำค้นหา
    category = request.GET.get('category', 'all')  # รับหมวดหมู่
    page_number = request.GET.get('page', 1)  # รับหมายเลขหน้า

    # ดึงหมวดหมู่ทั้งหมดที่มีอยู่ในฐานข้อมูล
    categories = Category.objects.all()  # ดึงหมวดหมู่ทั้งหมดจากฐานข้อมูล

    # ดึงสินค้าทั้งหมด
    products = Product.objects.all()

    # กรองสินค้าตามคำค้นหา (query)
    if query:
        products = products.filter(Q(product_name__icontains=query) | Q(description__icontains=query))

    # กรองสินค้าตามหมวดหมู่
    if category != 'all':
        products = products.filter(category__name=category)

    # แบ่งสินค้าเป็นหน้าละ 10 รายการ
    paginator = Paginator(products, 10)
    page_obj = paginator.get_page(page_number)

    # ดึงคำสั่งซื้อที่ยังไม่สมบูรณ์ล่าสุด
    order = Order.objects.filter(customer_name='unknown').last()

    total_price = 0
    total_quantity = 0
    if order:
        total_price = sum(detail.price for detail in order.order_details.all())
        total_quantity = sum(detail.quantity for detail in order.order_details.all())

    # ฟอร์มสำหรับกรอกข้อมูลลูกค้า
    form = CustomerInfoForm()

    # ส่งข้อมูล options_list ในแต่ละ product ไปยัง template
    for product in page_obj:
        # ใช้ .all() เพื่อดึงข้อมูล options ที่เชื่อมโยงกับ product
        product.options_list = [option.name for option in product.options.all()] if product.options.exists() else []

    return render(request, 'home.html', {
        'page_obj': page_obj,
        'query': query,
        'category': category,
        'categories': categories,  # ส่งหมวดหมู่ทั้งหมด
        'order': order,
        'total_price': total_price,
        'total_quantity': total_quantity,
        'form': form,  # ส่งฟอร์มข้อมูลลูกค้า
    })

# Add product to order
@csrf_exempt
@login_required
def add_to_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        options = data.get('options', [])  # Array of selected options
        quantity = data.get('quantity', 1)

        try:
            # Get the product
            product = Product.objects.get(id=product_id)

            # Retrieve or create an order for the logged-in user
            order, created = Order.objects.get_or_create(
                customer_name='unknown',  # Static name or use request.user.username if needed
                customer_phone='0999999999',  # Static phone number or use a profile field if needed
                defaults={'total_price': 0}
            )

            # Fetch the selected options from the database
            selected_options = Option.objects.filter(name__in=options, product=product)
            total_option_price = sum([option.price for option in selected_options])

            # Calculate the total price with options
            total_price = (product.price + total_option_price) * quantity

            # Check if the product with selected options already exists in the order
            order_detail = OrderDetail.objects.filter(
                order=order,
                product=product
            ).filter(options__in=selected_options).distinct()

            if order_detail.exists():
                # If product already exists in the order with the same options, update it
                order_detail = order_detail.first()  # Get the first matching order detail
                order_detail.quantity += quantity
                order_detail.price = order_detail.quantity * (product.price + total_option_price)
                order_detail.save()

                # Set the options for this order item
                order_detail.options.set(selected_options)
                order_detail.save()
            else:
                # Create a new OrderDetail if no matching item is found
                order_detail = OrderDetail.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=total_price
                )
                order_detail.options.set(selected_options)  # Set the options for this order item
                order_detail.save()

            # Update the total price of the order
            order.total_price = sum([item.price for item in order.order_details.all()])
            order.save()

            return JsonResponse({'status': 'success', 'message': 'Product added to order successfully', 'total_price': order.total_price})

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
        form = CustomerInfoForm(request.POST)

        # Print form data for debugging
        print("Form Data:", request.POST)

        if form.is_valid():
            customer_name = form.cleaned_data['customer_name']
            customer_phone = form.cleaned_data['customer_phone']

            # Get the latest order or create a new one
            order = Order.objects.filter(customer_name='unknown').last()
            if order:
                # Update the order with customer info
                order.customer_name = customer_name
                order.customer_phone = customer_phone
                order.save()

                # Get the order details and total price
                order_details = OrderDetail.objects.filter(order=order)
                total_order_price = sum(detail.price for detail in order_details)

                # Pass order details and total price to the payment page
                return render(request, 'payment.html', {
                    'order': order,
                    'order_details': order_details,
                    'total_order_price': total_order_price,
                    'form': PaymentForm()  # Only render the payment form if the customer info is valid
                })
            else:
                messages.error(request, 'No active order found. Please try again.')
        else:
            # Log the form errors to understand what went wrong
            print("Form Errors:", form.errors)
            messages.error(request, 'Invalid form data. Please check and try again.')

    return redirect('home')


@login_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)  # Get form data (including options)
        if form.is_valid():
            product = form.save()
            option_names = request.POST.getlist('option_name[]')
            option_prices = request.POST.getlist('option_price[]')
            for name, price in zip(option_names, option_prices):
                Option.objects.create(product=product, name=name, price=price)

            messages.success(request, 'Product added successfully!')
            return redirect('add_product')  # Redirect after successful form submission
        else:
            print("Form is not valid", form.errors)
            messages.error(request, 'Form is not valid.')
    else:
        form = ProductForm()

    return render(request, 'Addmenu.html', {'form': form})
@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES, instance=product)

        if product_form.is_valid():
            # Save the product first
            product = product_form.save()

            # Update options (clear previous options)
            product.options.all().delete()

            # Save new options
            option_names = request.POST.getlist('option_name[]')
            option_prices = request.POST.getlist('option_price[]')

            for name, price in zip(option_names, option_prices):
                Option.objects.create(
                    product=product,
                    name=name,
                    price=price
                )

            messages.success(request, 'Product updated successfully!')
            return redirect('addmenu')  # Redirect after successful form submission
    else:
        product_form = ProductForm(instance=product)

    # Fetch existing options for the product
    options = product.options.values('name', 'price')  # Fetch existing options for the product
    options = [
        {
            'name': option['name'],
            'price': float(option['price'])  # Convert Decimal to float
        }
        for option in options
    ]

    # Pass the options as JSON to the template
    return render(request, 'component/edit_product.html', {
        'form': product_form,
        'product': product,
        'options': options,  # Send options as JSON
    })
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
        try:
            data = json.loads(request.body)
            category_name = data.get('category_name')

            if not category_name:
                return JsonResponse({'status': 'error', 'message': 'Category name is required'})

            # Check if category already exists
            if Category.objects.filter(name=category_name).exists():
                return JsonResponse({'status': 'error', 'message': 'Category already exists'})

            # Create new category
            category = Category.objects.create(name=category_name)
            return JsonResponse({'status': 'success', 'message': 'Category added successfully', 'category_name': category.name})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'invalid method'})
