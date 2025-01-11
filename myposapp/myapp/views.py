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
from datetime import datetime, timedelta


def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        # ใช้ Django Auth ในการตรวจสอบ username และ password
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # Ensure that user is associated with a store
            try:
                member = user.member_profile  # Access member profile via 'member_profile'
                if member.store:
                    return redirect('home')  # Redirect to the home page if store exists
                else:
                    messages.error(request, 'ผู้ใช้ไม่เชื่อมโยงกับร้านค้าใดๆ')
                    return redirect('login')
            except Member.DoesNotExist:
                messages.error(request, 'ไม่พบข้อมูลสมาชิก')
                return redirect('login')
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
        store_name = request.POST.get('store_name', '').strip()

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
            store = Store.objects.create(name=store_name, owner=user)
            Member.objects.create(user=user, store=store)
            messages.success(request, 'การลงทะเบียนสำเร็จ! กรุณาเข้าสู่ระบบ.')
            return redirect('login')
        except Exception as e:
            print(f"Error during registration: {e}")
            messages.error(request, 'เกิดข้อผิดพลาดในการลงทะเบียน กรุณาลองใหม่')

    return render(request, 'register.html')

@login_required
def Order1(request):
    # Fetch all orders with payment status as 'Success'
    store = request.user.member_profile.store
    orders = Order.objects.filter(
        payment__payment_status='Success',
        store=store,
        status='Pending'
    )

    # Pagination: Set the number of orders per page
    page_number = request.GET.get('page', 1)
    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page_obj = paginator.get_page(page_number)

    # Calculate the total quantity for each order
    for order in page_obj:
        total_quantity = sum(detail.quantity for detail in order.order_details.all())
        order.total_quantity = total_quantity  # Add total_quantity as a dynamic attribute

    return render(request, 'Order.html', {'page_obj': page_obj})

@login_required
def get_order_details(request, order_id):
    # Retrieve the order from the database
    order = get_object_or_404(Order, id=order_id)

    # Prepare order details to send back in JSON format
    order_details = [
        {
            'product_name': detail.product.product_name,
            'quantity': detail.quantity,
            'unit_price': str(detail.price),  # Returning unit price
            'total_item_price': str(detail.quantity * detail.price),  # Total price = unit price * quantity
            'options': [
                {'name': option.name, 'price': str(option.price)} for option in detail.options.all()
            ]
        }
        for detail in order.order_details.all()
    ]

    # Prepare the final data to send back
    data = {
        'order_id': order.id,
        'customer_name': order.customer_name,
        'customer_phone': order.customer_phone,
        'total_price': str(order.total_price),
        'status': "ชำระเรียบร้อย" if order.payment.payment_status == "Success" else "Pending",
        'order_details': order_details,
    }

    return JsonResponse(data)
@login_required
@csrf_exempt
def complete_order(request, order_id):
    # ดึงข้อมูลคำสั่งซื้อตาม ID
    order = get_object_or_404(Order, id=order_id)

    # ตรวจสอบให้แน่ใจว่าคำสั่งซื้อเป็นของร้านค้าของผู้ใช้ที่เข้าสู่ระบบ
    if order.store != request.user.member_profile.store:
        messages.error(request, 'คุณไม่มีสิทธิ์เปลี่ยนแปลงสถานะของคำสั่งซื้อนี้')
        return redirect('order')

    # อัปเดตสถานะคำสั่งซื้อเป็น 'Success'
    order.status = 'Success'
    order.save()

    messages.success(request, f'Order #{order.id} เสร็จสมบูรณ์เรียบร้อยแล้ว')
    return JsonResponse({'status': 'success', 'message': 'อัปเดตสถานะคำสั่งซื้อเป็นสำเร็จแล้ว'})
@login_required
@csrf_exempt
def PayNow(request, order_id):
    try:
        # Fetch the order object
        order = get_object_or_404(Order, id=order_id)
        store = request.user.member_profile.store

        if request.method == 'POST':
            form = CustomerInfoForm(request.POST)

            if form.is_valid():
                # Get the customer data from the form
                customer_name = form.cleaned_data['customer_name']
                customer_phone = form.cleaned_data['customer_phone']

                # Update the order with customer information
                order.customer_name = customer_name
                order.customer_phone = customer_phone
                order.store = store
                order.save()
                # Redirect to the payment page
                return redirect('payment', order_id=order.id)

            else:
                messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')

        else:
            # If not a POST request, render the form with the existing customer data (if available)
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
    order = get_object_or_404(Order, id=order_id)
    store = request.user.member_profile.store
    # Initialize total order price
    total_order_price = Decimal(0)

    # List to hold order details with updated price calculation
    order_details = []

    for detail in order.order_details.all():
        selected_options = detail.options.all()
        total_option_price = sum(option.price for option in selected_options)
        unit_price = detail.product.price + total_option_price
        total_item_price = unit_price * detail.quantity
        order_details.append({
            'product_name': detail.product.product_name,
            'quantity': detail.quantity,
            'unit_price': unit_price,
            'total_item_price': total_item_price,
            'options': selected_options,
        })
        total_order_price += total_item_price

    # Fetch the points configuration (how many points per baht)
    points_config = PointsConfig.objects.first()

    points_earned = 0
    if points_config:
        points_earned = int(total_order_price * points_config.points_per_baht)  # Calculate points earned

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
                'points_earned': points_earned,  # Pass the points earned to the template
            })

        # Calculate change
        change = amount_paid - total_order_price  # Both operands are Decimal

        # Save the payment details
        Payment.objects.create(
            order=order,
            amount=total_order_price,
            payment_method=payment_method,
            payment_status='Success' if change >= 0 else 'Failed',
            store=store,
        )

        # Update customer points if the customer is found
        if order.customer_phone:
            try:
                customer = customerMember.objects.get(phone=order.customer_phone)
                customer.points += points_earned
                customer.save()
                messages.success(request, f'ชำระเงินสำเร็จ! คุณได้รับ {points_earned} แต้ม.')
            except customerMember.DoesNotExist:
                messages.warning(request, 'ไม่พบข้อมูลลูกค้า')

        return redirect('order')

    return render(request, 'Payment.html', {
        'order': order,
        'order_details': order_details,
        'total_order_price': total_order_price,
        'points_earned': points_earned,  # Pass the points earned to the template
    })
@login_required
def print_receipt(request, order_id):
    # Get the order object
    order = get_object_or_404(Order, id=order_id)
    total_order_price = Decimal(0)
    order_details = []

    for detail in order.order_details.all():
        selected_options = detail.options.all()
        total_option_price = sum(option.price for option in selected_options)
        unit_price = detail.product.price + total_option_price
        total_item_price = unit_price * detail.quantity
        order_details.append({
            'product_name': detail.product.product_name,
            'quantity': detail.quantity,
            'unit_price': unit_price,
            'total_item_price': total_item_price,
            'options': selected_options,
        })
        total_order_price += total_item_price
    # Calculate the total order price

    # Fetch the points configuration (how many points per baht)
    points_config = PointsConfig.objects.first()
    points_earned = 0
    if points_config:
        points_earned = int(total_order_price * points_config.points_per_baht)  # Calculate points earned

    # Render the receipt template and pass the necessary context
    return render(request, 'print_receipt.html', {
        'order': order,
        'order_details': order_details,
        'total_order_price': total_order_price,
        'points_earned': points_earned,
    })
@login_required
def Marketing(request):
    return render(request, 'Marketing.html')

@login_required
def inventory(request):
    return render(request, 'inventory.html')

@login_required
def History_Order(request):
    store = request.user.member_profile.store  # Get the store associated with the logged-in user
    search_query = request.GET.get('search', '')  # Get the search query (Order ID, customer name, etc.)
    date_filter = request.GET.get('date_filter', '')  # Get the selected date filter (e.g., 'today', 'this_week')

    # Initialize the filter condition for orders
    orders = Order.objects.filter(store=store, payment__payment_status='Success')  # Default: all successful orders

    # Apply date filters
    if date_filter == 'today':
        today = datetime.today().date()
        orders = orders.filter(created_at__date=today)
    elif date_filter == 'this_week':
        today = datetime.today().date()
        start_of_week = today - timedelta(days=today.weekday())  # Get the start of the week
        end_of_week = start_of_week + timedelta(days=6)  # Get the end of the week
        orders = orders.filter(created_at__date__range=[start_of_week, end_of_week])
    elif date_filter == 'this_month':
        today = datetime.today()
        first_day_of_month = today.replace(day=1)  # Get the first day of the current month
        last_day_of_month = (first_day_of_month.replace(month=first_day_of_month.month + 1) - timedelta(days=1))  # Last day of the month
        orders = orders.filter(created_at__date__range=[first_day_of_month.date(), last_day_of_month.date()])
    elif date_filter == 'custom':
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
                orders = orders.filter(created_at__date__range=[start_date.date(), end_date.date()])
            except ValueError:
                pass  # If the date format is wrong, ignore the custom date filter

    # Apply search query filter
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(order_details__product__product_name__icontains=search_query) |
            Q(status__icontains=search_query)
        ).distinct()

    # Pagination: Set the number of orders per page
    page_number = request.GET.get('page', 1)
    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page_obj = paginator.get_page(page_number)

    return render(request, 'History_Order.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'date_filter': date_filter
    })


@login_required
def update_points_config(request):
    store = request.user.member_profile.store
    # Only allow admin to access this page
    if not request.user.is_superuser:
        return redirect('home')
    points_config, created = PointsConfig.objects.get_or_create(store=store)

    if request.method == 'POST':
        form = PointsConfigForm(request.POST, instance=points_config)
        if form.is_valid():
            form.save()
            messages.success(request, "บันทึกการตั้งค่าแต้มแล้ว!")
            return redirect("member")
        else:
            messages.success(request, "ตั้งค่าไม่สำเร็จ!")
            return redirect("member")
    else:
        form = PointsConfigForm(instance=points_config)

    return render(request, 'Member1.html', {'form': form})
@login_required
def Member1(request):
    # Get the PointsConfig instance to pass the form to the template
    points_config = PointsConfig.objects.first()  # Assuming only one instance exists
    form = PointsConfigForm(instance=points_config)
    store = request.user.member_profile.store

    # Handle searching for customers
    search_query = request.GET.get('search', '')
    if search_query:
        customers = customerMember.objects.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query),
            store=store
        )
    else:
        customers = customerMember.objects.filter(store=store)

    if request.method == "POST":
        form = CustomerMemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member.store = store
            member.save()
            messages.success(request, "สมาชิกใหม่ถูกเพิ่มแล้ว!")
            return redirect("member")
        else:
            messages.error(request, "กรุณากรอกข้อมูลให้ครบถ้วน")

    return render(request, 'Member1.html', {
        'customers': customers,
        'form': form,  # Pass the PointsConfigForm to the template
        'search_query': search_query,
    })


@login_required
def edit_member(request, member_id):
    customer = get_object_or_404(customerMember, id=member_id)

    if request.method == 'POST':
        form = CustomerMemberForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'ข้อมูลสมาชิกถูกอัพเดตแล้ว!')
            return redirect('member')
    else:
        form = CustomerMemberForm(instance=customer)

    return render(request, 'edit_member.html', {'form': form, 'customer': customer})


@login_required
def delete_member(request, member_id):
    customer = get_object_or_404(customerMember, id=member_id)
    customer.delete()
    messages.success(request, 'สมาชิกถูกลบออกจากระบบ!')
    return redirect('member')

@login_required
def Addmenu(request):
    search_query = request.GET.get('search', '')  # รับคำค้นหาจากฟอร์ม
    store = request.user.member_profile.store
    categories = Category.objects.filter(store=store)
    # ถ้าคำค้นหามีการระบุ
    if search_query:
        products = Product.objects.filter(
            Q(product_name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(description__icontains=search_query),
            store=store
        )
    else:
        # ถ้าไม่มีคำค้นหาก็ให้ดึงสินค้าทั้งหมด
        products = Product.objects.filter(store=store)

    # การแบ่งหน้า
    page_number = request.GET.get('page', 1)  # รับค่าหน้าจาก query string
    paginator = Paginator(products, 12)  # แบ่งสินค้าเป็นหน้าละ 12 รายการ
    page_obj = paginator.get_page(page_number)

    form = ProductForm()  # ฟอร์มสำหรับการเพิ่มสินค้า

    return render(request, 'Addmenu.html', {'products': page_obj, 'form': form, 'search_query': search_query, 'categories': categories})

@login_required
def home(request):
    query = request.GET.get('q', '')  # รับค่าคำค้นหา
    category = request.GET.get('category', 'all')  # รับหมวดหมู่
    page_number = request.GET.get('page', 1)  # รับหมายเลขหน้า
    store = request.user.member_profile.store
    # ดึงหมวดหมู่ทั้งหมดที่มีอยู่ในฐานข้อมูล
    categories = Category.objects.filter(store=store)  # ดึงหมวดหมู่ทั้งหมดจากฐานข้อมูล

    # ดึงสินค้าทั้งหมด
    products = Product.objects.filter(store=store)

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
    order = Order.objects.filter(customer_name=' ').last()

    total_price = 0
    total_quantity = 0
    customer_points = 0  # Variable to store customer points

    if order:
        total_price = sum(detail.price for detail in order.order_details.all())
        total_quantity = sum(detail.quantity for detail in order.order_details.all())

        # Retrieve the points of the customer
        if order.customer_phone:
            try:
                # Fetch the customer using the phone number
                customer = customerMember.objects.get(phone=order.customer_phone)
                customer_points = customer.points  # Get the points of the customer
            except customerMember.DoesNotExist:
                customer_points = 0  # If the customer does not exist, set points to 0

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
        'customer_points': customer_points,  # Pass customer points to the template
        'form': form,  # ส่งฟอร์มข้อมูลลูกค้า
    })

@login_required
def search_member(request):
    search_query = request.GET.get('search', '').strip()
    store = request.user.member_profile.store

    if search_query:
        customers = customerMember.objects.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(points__icontains=search_query)
        ,store=store)
    else:
        customers = customerMember.objects.none()  # ไม่มีการค้นหาหรือคำค้นหาเป็นค่าว่าง

    # เตรียมข้อมูลของลูกค้าเพื่อส่งกลับ
    customer_data = [{
        'name': customer.name,
        'phone': customer.phone,
        'email': customer.email,
        'points': customer.points,
        'id': customer.id  # รวม ID ของลูกค้า
    } for customer in customers]

    return JsonResponse({'status': 'success', 'customers': customer_data})
# Add product to order
@csrf_exempt
@login_required
def add_to_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        options = data.get('options', [])  # Array ของตัวเลือกที่เลือก
        quantity = data.get('quantity', 1)

        try:
            # Get the product
            product = Product.objects.get(id=product_id)

            # Retrieve or create an order for the logged-in user
            order, created = Order.objects.get_or_create(
                customer_name=' ',
                customer_phone=' ',
                defaults={'total_price': 0}
            )

            # Fetch the selected options from the database
            selected_options = Option.objects.filter(name__in=options, product=product)
            total_option_price = sum([option.price for option in selected_options])

            # Calculate the total price with options
            total_price = (product.price + total_option_price) * quantity

            # Handle the case where no options are selected (treat it as a single product)
            if not selected_options:
                order_detail = OrderDetail.objects.filter(
                    order=order,
                    product=product,
                    options=None  # No options, just the product itself
                )
            else:
                # Handle the case where options are selected (treat it as a unique combination)
                order_detail = OrderDetail.objects.filter(
                    order=order,
                    product=product,
                    options__in=selected_options
                )

            # If no matching order detail exists (with the same options), create a new one
            if not order_detail.exists():
                order_detail = OrderDetail.objects.create(
                    order=order,
                    product=product,  # Ensure that the product is being properly assigned
                    quantity=quantity,
                    price=total_price
                )
                order_detail.options.set(selected_options)  # Set the options for this order item
                order_detail.save()
            else:
                # If the order detail with the same options exists, just update the quantity and price
                order_detail = order_detail.first()
                order_detail.quantity += quantity
                order_detail.price = order_detail.quantity * (product.price + total_option_price)
                order_detail.save()

            #อัพเดทราคารวมออเดอร์
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

            #ดึงรายละเอียดการสั่งซื้อ
            order_detail = get_object_or_404(OrderDetail, id=order_detail_id)

            # ดึงตัวเลือกที่เลือกและคำนวณราคาตัวเลือกทั้งหมด
            selected_options = order_detail.options.all()
            total_option_price = sum(option.price for option in selected_options)

            # คำนวณราคาใหม่ตามปริมาณและตัวเลือก
            total_price = (order_detail.product.price + total_option_price) * quantity

            # อัพเดทรายละเอียดการสั่งซื้อจำนวนและราคา
            order_detail.quantity = quantity
            order_detail.price = total_price
            order_detail.save()

            # คำนวณราคารวมของคำสั่งซื้อทั้งหมดอีกครั้ง
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
        form = ProductForm(request.POST, request.FILES)  # รับข้อมูลแบบฟอร์ม (รวมถึงตัวเลือก)
        if form.is_valid():
            product = form.save(commit=False)
            store = request.user.member_profile.store  # Get the store associated with the user
            product.store = store  # Associate product with the user's store
            product.save()
            option_names = request.POST.getlist('option_name[]')
            option_prices = request.POST.getlist('option_price[]')
            for name, price in zip(option_names, option_prices):
                Option.objects.create(product=product, name=name, price=price)

            messages.success(request, 'Product added successfully!')
            return redirect('add_product')  # เปลี่ยนเส้นทางหลังจากส่งแบบฟอร์มสำเร็จ
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
            #บันทึกสินค้าไว้ก่อน
            product = product_form.save()

            # อัปเดตตัวเลือก (ล้างตัวเลือกก่อนหน้า)
            product.options.all().delete()

            # บันทึกตัวเลือกใหม่
            option_names = request.POST.getlist('option_name[]')
            option_prices = request.POST.getlist('option_price[]')

            for name, price in zip(option_names, option_prices):
                Option.objects.create(
                    product=product,
                    name=name,
                    price=price
                )

            messages.success(request, 'Product updated successfully!')
            return redirect('addmenu')  # เปลี่ยนเส้นทางหลังจากส่งแบบฟอร์มสำเร็จ
    else:
        product_form = ProductForm(instance=product)

    #ดึงตัวเลือกที่มีอยู่สำหรับ product
    options = product.options.values('name', 'price')  #ดึงตัวเลือกที่มีอยู่สำหรับ product
    options = [
        {
            'name': option['name'],
            'price': float(option['price'])
        }
        for option in options
    ]

    # ส่งตัวเลือกเป็น JSON ไปยังเทมเพลต
    return render(request, 'component/edit_product.html', {
        'form': product_form,
        'product': product,
        'options': options,  # ส่งตัวเลือกเป็น JSON
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
            store = request.user.member_profile.store
            # ตรวจสอบว่ามีหมวดหมู่อยู่แล้วหรือไม่
            if Category.objects.filter(name=category_name, store=store).exists():
                return JsonResponse({'status': 'error', 'message': 'Category already exists'})

            # สร้างหมวดหมู่ใหม่
            category = Category.objects.create(name=category_name, store=store)
            return JsonResponse({'status': 'success', 'message': 'Category added successfully', 'category_name': category.name})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'invalid method'})
