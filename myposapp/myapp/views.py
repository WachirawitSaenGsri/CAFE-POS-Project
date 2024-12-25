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
from django.core.paginator import Paginator
from .forms import *
from django.db import transaction
from myapp.models import *

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

@login_required
def Menu(request):
    products = Product.objects.all()  # ดึงข้อมูลสินค้าทั้งหมดจากฐานข้อมูล
    return render(request, 'home.html', {'products': products})


@login_required
def Order1(request):
    # Fetch all orders
    orders = Order.objects.filter(payment__payment_status='Success')

    # For each order, calculate the total quantity of items
    for order in orders:
        total_quantity = sum(detail.quantity for detail in order.order_details.all())
        order.total_quantity = total_quantity  # Add total_quantity as a dynamic attribute

    return render(request, 'Order.html', {'orders': orders})

@login_required
def get_order_details(request, order_id):
    # ดึงข้อมูลคำสั่งซื้อจากฐานข้อมูลตาม order_id
    order = get_object_or_404(Order, id=order_id)

    # เตรียมข้อมูลคำสั่งซื้อที่ต้องการส่งกลับไปในรูปแบบ JSON
    order_details = [
        {
            'product_name': detail.product.product_name,
            'quantity': detail.quantity,
            'price': str(detail.price),
            'total_item_price': str(detail.quantity * detail.price),
            'options': [
                {'name': option.name, 'price': str(option.price)} for option in detail.options.all()
            ]
        }
        for detail in order.order_details.all()
    ]

    # ส่งข้อมูลคำสั่งซื้อและรายละเอียดกลับไป
    data = {
        'order_id': order.id,
        'customer_name': order.customer_name,
        'customer_phone': order.customer_phone,
        'total_price': str(order.total_price),
        'status': "Paid" if order.payment.payment_status == "Success" else "Pending",
        'order_details': order_details,
    }

    return JsonResponse(data)

@login_required
@csrf_exempt
def PayNow(request, order_id):
    try:
        # ดึงข้อมูลคำสั่งซื้อจากฐานข้อมูลตาม order_id
        order = get_object_or_404(Order, id=order_id)

        if request.method == 'POST':
            # สร้างฟอร์มจากข้อมูลที่รับมาใน POST
            form = CustomerInfoForm(request.POST)

            if form.is_valid():
                # รับข้อมูลจากฟอร์ม
                customer_name = form.cleaned_data['customer_name']
                customer_phone = form.cleaned_data['customer_phone']

                # อัปเดตข้อมูลลูกค้าในคำสั่งซื้อ
                order.customer_name = customer_name
                order.customer_phone = customer_phone
                order.save()

                # หลังจากบันทึกข้อมูลลูกค้าแล้ว ให้ไปยังหน้า payment
                return redirect('payment', order_id=order.id)

            else:
                messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')

        else:
            # หากไม่ใช่ POST ให้แสดงฟอร์มที่มีข้อมูลลูกค้าจากคำสั่งซื้อ
            form = CustomerInfoForm(initial={
                'customer_name': order.customer_name,
                'customer_phone': order.customer_phone,
            })

    except Exception as e:
        print(f"Error occurred while processing the payment: {e}")
        messages.error(request, 'เกิดข้อผิดพลาดในการชำระเงิน กรุณาลองใหม่อีกครั้ง')
        return redirect('home')

    return render(request, 'Payment.html', {
        'form': form,
        'order': order,
    })

from decimal import Decimal

@transaction.atomic
@login_required
def PayMent(request, order_id):
    # Get the order from the database
    order = get_object_or_404(Order, id=order_id)

    # Initialize total order price
    total_order_price = Decimal(0)  # Ensure this is a Decimal

    # List to hold order details with updated price calculation
    order_details = []

    # Loop through order details and calculate the unit price (product price + option prices)
    for detail in order.order_details.all():
        # Get the selected options for this product
        selected_options = detail.options.all()
        # Calculate the total option price
        total_option_price = sum(option.price for option in selected_options)

        # Calculate the unit price (base price of product + total price of selected options)
        unit_price = detail.product.price + total_option_price

        # Calculate the total price for this item (unit price * quantity)
        total_item_price = unit_price * detail.quantity

        # Update the order details with calculated prices
        order_details.append({
            'product_name': detail.product.product_name,
            'quantity': detail.quantity,
            'unit_price': unit_price,
            'total_item_price': total_item_price,
            'options': selected_options,
        })

        # Add the total item price to the overall total order price
        total_order_price += total_item_price

    # If the form is submitted, process the payment
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', None)
        amount_paid = Decimal(request.POST.get('amount_paid', 0))  # Convert amount_paid to Decimal

        if not payment_method or not amount_paid:
            messages.error(request, 'กรุณากรอกข้อมูลการชำระเงินให้ครบถ้วน')
            return render(request, 'Payment.html', {
                'order': order,
                'order_details': order_details,
                'total_order_price': total_order_price,
            })

        # Calculate change
        change = amount_paid - total_order_price  # Both operands are Decimal

        # Save the payment details
        Payment.objects.create(
            order=order,
            amount=total_order_price,
            payment_method=payment_method,
            payment_status='Success' if change >= 0 else 'Failed',
        )

        # Redirect to order history page after successful payment
        return redirect('order')

    # Render the payment page with order details
    return render(request, 'Payment.html', {
        'order': order,
        'order_details': order_details,
        'total_order_price': total_order_price,
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
    order = Order.objects.filter(customer_name='').last()

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

    # Check if order exists and pass it to the template
    return render(request, 'home.html', {
        'page_obj': page_obj,
        'query': query,
        'category': category,
        'categories': categories,  # ส่งหมวดหมู่ทั้งหมด
        'order': order if order else None,  # Ensure order is not None
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
                customer_name='',  # Static name or use request.user.username if needed
                customer_phone='',  # Static phone number or use a profile field if needed
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
                    product=product,  # Ensure that the product is being properly assigned
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

            # Fetch the order detail
            order_detail = get_object_or_404(OrderDetail, id=order_detail_id)

            # Fetch selected options and calculate the total option price
            selected_options = order_detail.options.all()
            total_option_price = sum(option.price for option in selected_options)

            # Recalculate the price based on quantity and options
            total_price = (order_detail.product.price + total_option_price) * quantity

            # Update the order detail's quantity and price
            order_detail.quantity = quantity
            order_detail.price = total_price
            order_detail.save()

            # Recalculate the total price of the entire order
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
