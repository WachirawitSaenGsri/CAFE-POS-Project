# myapp/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout ,authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Case, When
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.paginator import Paginator
from .forms import *
from django.db import transaction
from myapp.models import *
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Avg, F
from django.db.models.functions import TruncMonth, TruncYear
import stripe
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from reportlab.lib.pagesizes import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics  # แก้ไขที่นี่
import os
stripe.api_key = settings.STRIPE_SECRET_KEY

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        # ใช้ Django Auth ในการตรวจสอบ username และ password
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # ตรวจสอบให้แน่ใจว่าผู้ใช้เชื่อมโยงกับร้านค้า
            try:
                member = user.member_profile  # เข้าถึงโปรไฟล์สมาชิกผ่าน 'member_profile'
                if member.store:
                    if member.role == 'owner':
                        return redirect('home')  # เปลี่ยนเส้นทางไปยังหน้าแรกหากเป็นเจ้าของร้าน
                    elif member.role == 'employee':
                        return redirect('home_employee')  # เปลี่ยนเส้นทางไปยังหน้าแรกของพนักงาน
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
    # รับคำสั่งซื้อทั้งหมดที่มีสถานะการชำระเงินเป็น 'สำเร็จ'
    store = request.user.member_profile.store
    orders = Order.objects.filter(
        payment__payment_status='Success',
        store=store,
        status='Pending'
    )

    # Pagination: กำหนดจำนวนคำสั่งซื้อต่อหน้า
    page_number = request.GET.get('page', 1)
    paginator = Paginator(orders, 10)  # แสดง 10 คำสั่งซื้อต่อหน้า
    page_obj = paginator.get_page(page_number)

    # คำนวณปริมาณรวมสำหรับการสั่งซื้อแต่ละครั้ง
    for order in page_obj:
        total_quantity = sum(detail.quantity for detail in order.order_details.all())
        order.total_quantity = total_quantity

    return render(request, 'Order.html', {'page_obj': page_obj})

@login_required
def get_order_details(request, order_id):
    # ดึงข้อมูลคำสั่งซื้อจากฐานข้อมูล
    order = get_object_or_404(Order, id=order_id)

    # เตรียมรายละเอียดการสั่งซื้อเพื่อส่งกลับในรูปแบบ JSON
    order_details = [
        {
            'product_name': detail.product.product_name,
            'quantity': detail.quantity,
            'unit_price': str(detail.price),
            'total_item_price': str(detail.quantity * detail.price),
            'options': [
                {
                    'name': option.option.name,
                    'price': str(option.option.price),
                    'quantity': option.quantity
                } for option in detail.order_detail_options.all()
            ]
        }
        for detail in order.order_details.all()
    ]

    # เตรียมข้อมูลสุดท้ายเพื่อส่งกลับ
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

    return JsonResponse({'status': 'success', 'message': 'อัปเดตสถานะคำสั่งซื้อเป็นสำเร็จแล้ว'})
@login_required
@csrf_exempt
def PayNow(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)
        store = request.user.member_profile.store

        if request.method == 'POST':
            form = CustomerInfoForm(request.POST)

            if form.is_valid():
                # รับข้อมูลลูกค้าจากแบบฟอร์ม
                customer_name = form.cleaned_data['customer_name']
                customer_phone = form.cleaned_data['customer_phone']

                #อัพเดทออเดอร์พร้อมข้อมูลลูกค้า
                order.customer_name = customer_name
                order.customer_phone = customer_phone
                order.employee = request.user
                order.store = store
                order.save()
                # เปลี่ยนเส้นทางไปยังหน้าการชำระเงิน
                return redirect('payment', order_id=order.id)

            else:
                messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')

        else:
            # หากไม่ใช่คำขอ POST ให้แสดงแบบฟอร์มด้วยข้อมูลลูกค้าที่มีอยู่ (ถ้ามี)
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
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    endpoint_secret = 'whsec_6d275f1c0081983e0a2c87cae902d640fde9f94cbdeb18f89742a6e766cdc854'

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session(session)

    return JsonResponse({'status': 'success'})

def handle_checkout_session(session):
    pass
# views.py
@csrf_exempt
def create_checkout_session(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = data['order_id']
            amount = data['amount']
            currency = data['currency']

            order = Order.objects.get(id=order_id)

            session = stripe.checkout.Session.create(
                payment_method_types=['card', 'promptpay'],
                line_items=[{
                    'price_data': {
                        'currency': currency,
                        'product_data': {
                            'name': f'Order #{order_id}',
                        },
                        'unit_amount': int(amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri('/success/'),
                cancel_url=request.build_absolute_uri('/cancel/'),
            )

            return JsonResponse({'url': session.url})

        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=400)


def payment_success(request):
    return render(request, 'component/payment_success.html')

def payment_cancel(request):
    return render(request, 'component/payment_cancel.html')
@transaction.atomic
@login_required
def PayMent(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    store = request.user.member_profile.store
    total_order_price = Decimal(0)
    order_details = []

    for detail in order.order_details.all():
        selected_options = detail.order_detail_options.all()
        total_option_price = sum(opt.option.price * opt.quantity for opt in selected_options)
        unit_price = detail.product.get_discounted_price() + total_option_price
        total_item_price = unit_price * detail.quantity

        order_details.append({
            'product_name': detail.product.product_name,
            'quantity': detail.quantity,
            'unit_price': unit_price,
            'total_item_price': total_item_price,
            'options': [
                {'name': opt.option.name, 'price': opt.option.price, 'quantity': opt.quantity}
                for opt in selected_options
            ],
        })
        total_order_price += total_item_price

    points_config = PointsConfig.objects.first()
    points_earned = 0
    discount = Decimal(0)

    if points_config:
        points_earned = int(total_order_price * points_config.points_per_baht)

    customer = None
    customer_points = 0

    if order.customer_phone:
        try:
            customer = customerMember.objects.get(phone=order.customer_phone)
            customer_points = customer.points
        except customerMember.DoesNotExist:
            customer = None

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        amount_paid = Decimal(request.POST.get('amount_paid', 0))
        points_used = int(request.POST.get('points_used', '0'))  # ✅ ดึงค่าที่ใช้แต้มออกมา

        if customer and points_config and points_used > 0:
            if points_used > customer.points:
                messages.error(request, 'แต้มสะสมของคุณไม่เพียงพอ กรุณาลองใหม่')
                return redirect('payment', order_id=order.id)

            # ✅ คำนวณส่วนลดจากแต้ม
            discount = Decimal(points_used) / points_config.points_to_baht
            total_order_price -= discount
            if total_order_price < 0:
                total_order_price = 0  # ป้องกันราคาติดลบ

            # ✅ บันทึกแต้มที่ใช้ลงฐานข้อมูล
            order.points_used = points_used  # ✅ อัปเดตแต้มที่ใช้
            order.total_price = total_order_price  # ✅ อัปเดตราคาสุทธิหลังลดแต้ม
            order.save()  # ✅ บันทึกคำสั่งซื้ออัปเดตลงฐานข้อมูล

            # ✅ อัปเดตแต้มลูกค้า
            customer.points -= points_used
            customer.save()

        # ✅ คำนวณเงินทอน
        change = amount_paid - total_order_price

        # ✅ บันทึกการชำระเงิน
        Payment.objects.create(
            order=order,
            amount=total_order_price,  # ✅ ใช้ราคาที่ลดแล้ว
            payment_method=payment_method,
            payment_status='Success',
            store=store,
        )

        # ✅ ให้แต้มลูกค้าเพิ่มจากการสั่งซื้อ
        if customer:
            customer.points += points_earned
            customer.save()

        return redirect('order')

    return render(request, 'Payment.html', {
        'order': order,
        'order_details': order_details,
        'total_order_price': total_order_price,
        'discount': discount,
        'discounted_price': total_order_price,
        'points_earned': points_earned,
        'customer_points': customer_points,
        'points_config': points_config,
    })


def generate_receipt(request, order_id):
    # รับคำสั่งซื้อจากฐานข้อมูล
    order = Order.objects.get(id=order_id)

    # คำนวณราคาสั่งซื้อทั้งหมดและรายละเอียดคำสั่งซื้อ
    total_order_price = Decimal(0)
    order_details = []

    for detail in order.order_details.all():
        selected_options = detail.order_detail_options.all()
        total_option_price = sum(opt.option.price * opt.quantity for opt in selected_options)
        unit_price = detail.product.get_discounted_price() + total_option_price
        total_item_price = unit_price * detail.quantity

        order_details.append({
            'product_name': detail.product.product_name,
            'quantity': detail.quantity,
            'unit_price': unit_price,
            'total_item_price': total_item_price,
            'options': [
                {'name': opt.option.name, 'price': opt.option.price, 'quantity': opt.quantity}
                for opt in selected_options
            ],
        })
        total_order_price += total_item_price

    # ดึงการกำหนดค่าคะแนน (บาทละกี่คะแนน)
    points_config = PointsConfig.objects.first()
    points_earned = 0
    if points_config:
        points_earned = int(total_order_price * points_config.points_per_baht)  # คำนวณคะแนนที่ได้รับ

    # กำหนดขนาดของสลิปที่ต้องการ (80mm x 200mm = 3.15 inches x 7.87 inches)
    width, height = 3.15 * inch, 7.87 * inch  # ขนาดที่ตั้งเป็นนิ้ว (inch)

    # กำหนดการตั้งค่า PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{order.id}.pdf"'

    # ฟอนต์ที่ใช้
    font_path = os.path.join('D:/CAFE-POS-Project/THSarabunNew', 'THSarabunNew.ttf')  # ระบุ path ฟอนต์ที่คุณมี
    pdfmetrics.registerFont(TTFont('THSarabun', font_path))

    # สร้าง canvas ด้วยขนาดที่กำหนด
    pdf = canvas.Canvas(response, pagesize=(width, height))

    # กำหนดฟอนต์
    pdf.setFont("THSarabun", 10)
    thai_months = ['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน',
                   'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม']

    day_th = order.created_at.day
    month_th = thai_months[order.created_at.month - 1]
    year_th = order.created_at.year
    # ข้อมูลส่วนหัว (ปรับตำแหน่งให้ตรงกลาง)
    pdf.setFont("THSarabun", 10)
    order_id_text = f"หมายเลขคำสั่งซื้อ: {order.id}"
    customer_name_text = f"ชื่อลูกค้า: {order.customer_name}"
    customer_phone_text = f"เบอร์โทรศัพท์: {order.customer_phone}"
    date_text = f"วันที่: {day_th} {month_th} {year_th}"
    store_name_text = f"ร้าน: {order.store.name}"

    pdf.drawString((width - pdf.stringWidth(order_id_text)) / 2, height - 30, order_id_text)
    pdf.drawString((width - pdf.stringWidth(customer_name_text)) / 2, height - 50, customer_name_text)
    pdf.drawString((width - pdf.stringWidth(customer_phone_text)) / 2, height - 70, customer_phone_text)
    pdf.drawString((width - pdf.stringWidth(date_text)) / 2, height - 90, date_text)
    pdf.drawString((width - pdf.stringWidth(store_name_text)) / 2, height - 110, store_name_text)

    # กำหนดตำแหน่งของตารางสินค้า
    y_position = height - 130

    # สร้างหัวตาราง
    pdf.setFont("THSarabun", 10)
    pdf.drawString(15, y_position, "สินค้า")
    pdf.drawString(60, y_position, "ตัวเลือก")
    pdf.drawString(110, y_position, "จำนวน")
    pdf.drawString(140, y_position, "ราคาต่อหน่วย")
    pdf.drawString(190, y_position, "ราคารวม")

    # เปลี่ยนตำแหน่ง y เพื่อให้เขียนข้อมูลใต้หัวตาราง
    y_position -= 20

    # ฟังก์ชั่นเพื่อทำการแบ่งบรรทัดอัตโนมัติ
    def wrap_text(text, width_limit):
        lines = []
        words = text.split(" | ")
        current_line = words[0]

        for word in words[1:]:
            if pdf.stringWidth(current_line + " | " + word) < width_limit:
                current_line += " | " + word
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        return lines
    # วนลูปผ่านรายละเอียดคำสั่งซื้อ
    pdf.setFont("THSarabun", 9)
    for detail in order_details:
        product_name = detail['product_name']
        quantity = detail['quantity']
        unit_price = detail['unit_price']
        total_price = detail['total_item_price']
        options = " | ".join([f"{opt['name']} x {opt['quantity']}" for opt in detail['options']])

        # แสดงข้อมูลสินค้าในตาราง
        pdf.drawString(15, y_position, product_name)
        pdf.drawString(120, y_position, str(quantity))
        pdf.drawString(150, y_position, f"{unit_price:.2f} ฿")
        pdf.drawString(190, y_position, f"{total_price:.2f} ฿")

        # แบ่งตัวเลือกเป็นหลายบรรทัดหากข้อความยาวเกินไป
        options_lines = wrap_text(options if options else "ไม่มีตัวเลือก", 60)

        # แสดงตัวเลือกที่ย้ายไปยังตำแหน่งที่ต้องการ
        for line in options_lines:
            pdf.drawString(60, y_position, line)
            y_position -= 15  # ลดตำแหน่ง y ลงเพื่อไปที่บรรทัดถัดไป

        # ย้ายลงมาทีละ 20
        y_position -= 20

        # เพิ่มการตรวจสอบว่า y_position ต่ำไปหรือไม่
        if y_position < 40:
            pdf.showPage()
            pdf.setFont("THSarabun", 9)
            y_position = height - 30
            pdf.drawString(20, y_position, f"หมายเลขคำสั่งซื้อ: {order.id}")
            y_position -= 20

    # ข้อมูลส่วนท้าย
    y_position -= 40
    pdf.setFont("THSarabun", 12)
    pdf.drawString(10, y_position, f"ราคาสั่งซื้อทั้งหมด: {total_order_price:.2f} ฿")
    pdf.drawString(10, y_position - 20, f"คะแนนที่ได้รับ: {points_earned} แต้ม")

    # เพิ่มเส้นขอบ (เพื่อความสวยงาม)
    pdf.setLineWidth(0.5)
    pdf.line(10, height - 10, width - 10, height - 10)
    pdf.line(10, height - 120, width - 10, height - 120)
    pdf.line(10, height - 140, width - 10, height - 140)

    # สร้าง PDF และส่งออก
    pdf.showPage()
    pdf.save()

    return response

@login_required
def print_receipt(request, order_id):
    # Get the order object
    order = get_object_or_404(Order, id=order_id)
    total_order_price = Decimal(0)
    order_details = []

    for detail in order.order_details.all():
        selected_options = detail.order_detail_options.all()
        total_option_price = sum(opt.option.price * opt.quantity for opt in selected_options)
        unit_price = detail.product.get_discounted_price() + total_option_price
        total_item_price = unit_price * detail.quantity

        order_details.append({
            'product_name': detail.product.product_name,
            'quantity': detail.quantity,
            'unit_price': unit_price,
            'total_item_price': total_item_price,
            'options': [
                {'name': opt.option.name, 'price': opt.option.price, 'quantity': opt.quantity}
                for opt in selected_options
            ],
        })
        total_order_price += total_item_price
    # คำนวณราคาสั่งซื้อทั้งหมด

    # ดึงการกำหนดค่าคะแนน (บาทละกี่คะแนน)
    points_config = PointsConfig.objects.first()
    points_earned = 0
    if points_config:
        points_earned = int(total_order_price * points_config.points_per_baht)  # คำนวณคะแนนที่ได้รับ

    # แสดงผลเทมเพลตใบเสร็จรับเงินและส่งต่อ context
    return render(request, 'print_receipt.html', {
        'order': order,
        'order_details': order_details,
        'total_order_price': total_order_price,
        'points_earned': points_earned,
    })
@login_required
def Marketing(request):
    store = request.user.member_profile.store
    filter_by = request.GET.get('filter', 'all')  # ตัวกรองเริ่มต้น
    start_date = request.GET.get('start_date')  # วันที่เริ่มต้น
    end_date = request.GET.get('end_date')  # วันที่สิ้นสุด
    today = datetime.today()

    # ตั้งค่าวันที่เริ่มต้นตามตัวกรอง
    if filter_by == 'day':
        start_date = today
    elif filter_by == 'week':
        start_date = today - timedelta(days=today.weekday())
    elif filter_by == 'month':
        start_date = today.replace(day=1)

    # แปลงวันที่จาก string เป็น datetime object
    if start_date and isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date and isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d")

    # ดึงคำสั่งซื้อตามเงื่อนไข
    if start_date and end_date:
        orders = Order.objects.filter(store=store, created_at__date__range=[start_date, end_date])
    elif start_date:
        orders = Order.objects.filter(store=store, created_at__date__gte=start_date)
    else:
        orders = Order.objects.filter(store=store)

    # คำนวณสถิติการขาย
    total_orders = orders.count()
    total_revenue = orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0

    # รายการขายดีที่สุด
    best_selling_items = OrderDetail.objects.filter(order__store=store, order__in=orders).values(
        'product__product_name'
    ).annotate(
        total_sales=Sum('quantity')
    ).order_by('-total_sales')

    best_selling_item = best_selling_items[0]['product__product_name'] if best_selling_items else "No Sales"

    # รายการขายรายเดือน
    monthly_revenue = (
        orders.annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total_revenue=Sum('total_price'))
        .order_by('month')
    )
    months = [sale['month'].strftime("%B %Y") for sale in monthly_revenue if sale['month']]
    revenue_by_month = [float(sale['total_revenue']) for sale in monthly_revenue]

    # รายการขายดีที่สุดตามหมวดหมู่
    category_sales = (
        OrderDetail.objects.filter(order__store=store, order__in=orders)
        .values('product__category__name')
        .annotate(total_sales=Sum('quantity'))
        .order_by('-total_sales')
    )
    top_categories = [item['product__category__name'] for item in category_sales if item['product__category__name']]
    sales_by_category = [int(item['total_sales']) for item in category_sales]

    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'average_order_value': round(average_order_value, 2),
        'best_selling_item': best_selling_item,
        'menu_names': [item['product__product_name'] for item in best_selling_items[:5]],
        'menu_sales': [item['total_sales'] for item in best_selling_items[:5]],
        'filter_by': filter_by,
        'start_date': start_date.strftime("%Y-%m-%d") if start_date else '',
        'end_date': end_date.strftime("%Y-%m-%d") if end_date else '',
        'months': months,
        'revenue_by_month': revenue_by_month,
        'top_categories': top_categories,
        'sales_by_category': sales_by_category,
    }
    return render(request, 'Marketing.html', context)

@login_required
def History_Order(request):
    store = request.user.member_profile.store  # รับร้านค้าที่เกี่ยวข้องกับผู้ใช้ที่เข้าสู่ระบบ
    search_query = request.GET.get('search', '')  # รับคำค้นหา (รหัสคำสั่งซื้อ ชื่อลูกค้า ฯลฯ)
    date_filter = request.GET.get('date_filter', '')  # รับตัวกรองวันที่ที่เลือก (เช่น 'today', 'this_week')

    ## เริ่มต้นเงื่อนไขตัวกรองสำหรับคำสั่งซื้อที่สำเร็จ
    orders = Order.objects.filter(store=store, payment__payment_status='Success')  # ค่าเริ่มต้น: คำสั่งซื้อที่สำเร็จทั้งหมด

    # ใช้ตัวกรองวันที่
    if date_filter == 'today':
        today = datetime.today().date()
        orders = orders.filter(created_at__date=today)
    elif date_filter == 'this_week':
        today = datetime.today().date()
        start_of_week = today - timedelta(days=today.weekday())  #เริ่มต้นสัปดาห์
        end_of_week = start_of_week + timedelta(days=6)  # ท้ายสัปดาห์
        orders = orders.filter(created_at__date__range=[start_of_week, end_of_week])
    elif date_filter == 'this_month':
        today = datetime.today()
        first_day_of_month = today.replace(day=1)  # รับวันแรกของเดือนปัจจุบัน
        last_day_of_month = (first_day_of_month.replace(month=first_day_of_month.month + 1) - timedelta(days=1))  #วันสุดท้ายของเดือน
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
                pass  # ไม่ต้องทำอะไรถ้าเกิดข้อผิดพลาด

    # ใช้คำค้นหา
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(order_details__product__product_name__icontains=search_query) |
            Q(status__icontains=search_query)
        ).distinct()

    # การแบ่งหน้า
    page_number = request.GET.get('page', 1)
    paginator = Paginator(orders, 10)  # แบ่งคำสั่งซื้อเป็นหน้าละ 10 รายการ
    page_obj = paginator.get_page(page_number)

    return render(request, 'History_Order.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'date_filter': date_filter,

    })


@login_required
def update_points_config(request):
    store = request.user.member_profile.store  # รับร้านค้าที่เกี่ยวข้องกับผู้ใช้
    points_config, created = PointsConfig.objects.get_or_create(store=store)

    if request.method == 'POST':
        form = PointsConfigForm(request.POST, instance=points_config)
        if form.is_valid():
            form.save()
            messages.success(request, "บันทึกการตั้งค่าแต้มสำเร็จ!")
            return redirect("member")  # รีเฟรชหน้า Member1 หลังจากบันทึก
        else:
            messages.error(request, "เกิดข้อผิดพลาด! กรุณาลองใหม่")

    else:
        form = PointsConfigForm(instance=points_config)

    return render(request, 'Member1.html', {'form': form})
@login_required
def Member1(request):
    # ดึงข้อมูลการตั้งค่าแต้ม
    points_config = PointsConfig.objects.first()  # รับการตั้งค่าแต้มแรกที่พบ
    form = PointsConfigForm(instance=points_config)
    store = request.user.member_profile.store

    #จัดการการค้นหาลูกค้า
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
    paginator = Paginator(customers, 10)  # Show 10 employees per page
    page_number = request.GET.get('page')  # Get the current page number
    page_obj = paginator.get_page(page_number)
    evaluation_data = []
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
        'customers': page_obj.object_list,
        'form': form,
        'search_query': search_query,
        'page_obj': page_obj,
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
    member = request.user.member_profile
    if member.role == 'employee':
        return redirect('member_employee')
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
    customer_points = 0  # ตัวแปรในการเก็บคะแนนลูกค้า

    if order:
        total_price = sum(detail.price for detail in order.order_details.all())
        total_quantity = sum(detail.quantity for detail in order.order_details.all())

        # ดึงคะแนนของลูกค้า
        if order.customer_phone:
            try:
               # ดึงข้อมูลลูกค้าจากเบอร์โทร
                customer = customerMember.objects.get(phone=order.customer_phone)
                customer_points = customer.points # ดึงคะแนนลูกค้า
            except customerMember.DoesNotExist:
                customer_points = 0  # ถ้าไม่พบข้อมูลลูกค้าให้คะแนนเป็น 0

    # ฟอร์มสำหรับกรอกข้อมูลลูกค้า
    form = CustomerInfoForm()

    # ส่งข้อมูล options_list ในแต่ละ product ไปยัง template
    for product in page_obj:
        # ใช้ .all() เพื่อดึงข้อมูล options ที่เชื่อมโยงกับ product
        product.options_list = [option.name for option in product.options.all()] if product.options.exists() else []
        product.discounted_price = product.get_discounted_price()  # คำนวณราคาสินค้าหลังหักส่วนลด

    # ส่งข้อมูลไปยัง template
    return render(request, 'home.html', {
        'page_obj': page_obj,
        'query': query,
        'category': category,
        'categories': categories,  # ส่งหมวดหมู่ทั้งหมด
        'order': order if order else None,  # ส่งคำสั่งซื้อล่าสุดไปยัง template
        'total_price': total_price,
        'total_quantity': total_quantity,
        'customer_points': customer_points,  # ส่งคะแนนลูกค้าไปยัง template
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
#สั่งสินค้าเพิ่ม
# myapp/views.py
@csrf_exempt
@login_required
def add_to_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        options = data.get('options', [])  # List ของตัวเลือกที่เลือก
        quantity = data.get('quantity', 1)

        try:
            # รับสินค้า
            product = Product.objects.get(id=product_id)

            # ดึงหรือสร้างคำสั่งซื้อที่ยังไม่สมบูรณ์
            order, created = Order.objects.get_or_create(
                customer_name=' ',
                customer_phone=' ',
                defaults={'total_price': 0}
            )

            # ตรวจสอบวัตถุดิบก่อนสร้างคำสั่งซื้อ
            product_ingredients = ProductIngredient.objects.filter(product=product)
            for product_ingredient in product_ingredients:
                required_quantity = product_ingredient.quantity * quantity
                if product_ingredient.ingredient.stock < required_quantity:
                    return JsonResponse({'status': 'error', 'message': f'วัตถุดิบ {product_ingredient.ingredient.name} ไม่เพียงพอ'})

            # คำนวณราคาพื้นฐานของสินค้า
            base_price = product.get_discounted_price() * quantity
            total_option_price = 0

            # ตรวจสอบว่ามี OrderDetail เดิมที่ไม่มีตัวเลือกอยู่หรือไม่
            if not options:
                order_detail = OrderDetail.objects.filter(
                    order=order,
                    product=product
                ).first()
            else:
                # ตรวจสอบ OrderDetail ที่มีตัวเลือกตรงกัน
                order_detail = OrderDetail.objects.filter(
                    order=order,
                    product=product,
                    order_detail_options__option__in=[opt['option_id'] for opt in options]
                ).first()

            if order_detail:
                # ถ้ามีรายการเดิมอยู่แล้ว อัปเดตปริมาณและราคา
                order_detail.quantity += quantity
                order_detail.price += base_price
                order_detail.save()
            else:
                # ถ้ายังไม่มี ให้สร้างใหม่
                order_detail = OrderDetail.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=base_price
                )

            # จัดการตัวเลือกของสินค้า
            for option_data in options:
                option = get_object_or_404(Option, id=option_data['option_id'])
                option_quantity = int(option_data['quantity'])

                # ตรวจสอบว่ามีตัวเลือกนี้ใน `OrderDetailOption` อยู่แล้วหรือไม่
                order_detail_option, created = OrderDetailOption.objects.get_or_create(
                    order_detail=order_detail,
                    option=option,
                    defaults={'quantity': option_quantity}
                )

                # คำนวณราคาตัวเลือกทั้งหมด
                total_option_price += order_detail_option.total_price()

            # อัปเดตราคาสุทธิของ OrderDetail
            order_detail.price += total_option_price
            order_detail.save()

            # อัพเดทราคารวมของ Order
            order.total_price = sum(item.total_price() for item in order.order_details.all())
            order.save()

            # อัปเดตปริมาณวัตถุดิบหลังจากเพิ่มคำสั่งซื้อ
            for product_ingredient in product_ingredients:
                product_ingredient.ingredient.stock -= product_ingredient.quantity * quantity
                product_ingredient.ingredient.save()

            return JsonResponse({'status': 'success', 'message': 'เพิ่มสินค้าในคำสั่งซื้อสำเร็จ!', 'total_price': order.total_price})

        except Product.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'ไม่พบสินค้า'})
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
            new_quantity = int(data.get('quantity', 1))

            # รับรายละเอียดคำสั่งซื้อ
            order_detail = get_object_or_404(OrderDetail, id=order_detail_id)
            old_quantity = order_detail.quantity

            # คำนวณความแตกต่างในปริมาณ
            quantity_diff = new_quantity - old_quantity

            # ตรวจสอบวัตถุดิบเพียงพอหรือไม่
            product_ingredients = ProductIngredient.objects.filter(product=order_detail.product)
            for product_ingredient in product_ingredients:
                ingredient = product_ingredient.ingredient
                if ingredient.stock < product_ingredient.quantity * quantity_diff:
                    return JsonResponse({'status': 'error', 'message': f'วัตถุดิบ {ingredient.name} ไม่เพียงพอ'})

            # อัพเดตปริมาณวัตถุดิบ
            for product_ingredient in product_ingredients:
                ingredient = product_ingredient.ingredient
                ingredient.stock -= product_ingredient.quantity * quantity_diff
                ingredient.save()

            # คำนวณราคาใหม่
            total_option_price = sum(opt.option.price * opt.quantity for opt in order_detail.order_detail_options.all())
            unit_price = order_detail.product.get_discounted_price() + total_option_price
            total_price = unit_price * new_quantity

            order_detail.quantity = new_quantity
            order_detail.price = total_price
            order_detail.save()

            # อัพเดตราคารวมของคำสั่งซื้อ
            order_detail.order.total_price = sum(item.total_price() for item in order_detail.order.order_details.all())
            order_detail.order.save()

            return JsonResponse({
                'status': 'success',
                'message': 'อัปเดตคำสั่งซื้อสำเร็จ!',
                'new_quantity': order_detail.quantity,
                'new_price': order_detail.price,
                'total_order_price': order_detail.order.total_price
            })
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

            # ดึงรายละเอียดคำสั่งซื้อ
            order_detail = get_object_or_404(OrderDetail, id=order_detail_id)

            # คืนค่าวัตถุดิบกลับไป
            product_ingredients = ProductIngredient.objects.filter(product=order_detail.product)
            for product_ingredient in product_ingredients:
                ingredient = product_ingredient.ingredient
                ingredient.stock += product_ingredient.quantity * order_detail.quantity
                ingredient.save()

            # ลบตัวเลือกของสินค้า
            order_detail.order_detail_options.all().delete()

            # ลบรายละเอียดคำสั่งซื้อ
            order_detail.delete()

            # อัพเดตราคารวมของคำสั่งซื้อ
            order_detail.order.total_price = sum(item.total_price() for item in order_detail.order.order_details.all())
            order_detail.order.save()

            return JsonResponse({'status': 'success', 'message': 'ลบรายการสำเร็จ', 'total_order_price': order_detail.order.total_price})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'invalid method'})

@csrf_exempt
def cancel_order(request, order_id):
    if request.method == 'POST':
        try:
            order = Order.objects.get(id=order_id)
            order_details = OrderDetail.objects.filter(order=order)

            for detail in order_details:
                product_ingredients = ProductIngredient.objects.filter(product=detail.product)
                for product_ingredient in product_ingredients:
                    product_ingredient.ingredient.stock += product_ingredient.quantity * detail.quantity
                    product_ingredient.ingredient.save()

            order.delete()
            return JsonResponse({'status': 'success', 'message': 'Order cancelled and stock returned.'})
        except Order.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Order not found.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

@login_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)  # รับข้อมูลแบบฟอร์ม (รวมถึงตัวเลือก)
        if form.is_valid():
            product = form.save(commit=False)
            store = request.user.member_profile.store  # รับร้านค้าที่เกี่ยวข้องกับผู้ใช้
            product.store = store  # เชื่อมโยงสินค้ากับร้านค้า
            product.save()
            option_names = request.POST.getlist('option_name[]')
            option_prices = request.POST.getlist('option_price[]')
            for name, price in zip(option_names, option_prices):
                Option.objects.create(product=product, name=name, price=price)

            return redirect('add_product')  # เปลี่ยนเส้นทางหลังจากส่งแบบฟอร์มสำเร็จ
        else:
            print("แบบฟอร์มไม่ถูกต้อง", form.errors)
            messages.error(request, 'แบบฟอร์มไม่ถูกต้อง')
    else:
        form = ProductForm()

    return render(request, 'Addmenu.html', {'form': form})
@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    store = request.user.member_profile.store
    categories = Category.objects.filter(store=store)
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
        'categories': categories,
    })
# View สำหรับการลบสินค้า
@login_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect('addmenu')


@csrf_exempt
@login_required
def add_category(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            category_name = data.get('category_name')

            if not category_name:
                return JsonResponse({'status': 'error', 'message': 'ต้องระบุชื่อหมวดหมู่'})
            store = request.user.member_profile.store
            # ตรวจสอบว่ามีหมวดหมู่อยู่แล้วหรือไม่
            if Category.objects.filter(name=category_name, store=store).exists():
                return JsonResponse({'status': 'error', 'message': 'มีหมวดหมู่อยู่แล้ว'})

            # สร้างหมวดหมู่ใหม่
            category = Category.objects.create(name=category_name, store=store)
            return JsonResponse({'status': 'success', 'message': 'Category added successfully', 'category_name': category.name})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'invalid method'})

@login_required
def manage_ingredients(request):
    store = request.user.member_profile.store
    ingredients = Ingredient.objects.filter(store=store)  # ดึงข้อมูลวัตถุดิบทั้งหมดจากฐานข้อมูล
    page_number = request.GET.get('page', 1)
    paginator = Paginator(ingredients, 10)  # Show 10 ingredients per page
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        ingredient_id = request.POST.get('ingredient_id')  # รับ ingredient_id ที่ส่งมาจากฟอร์ม
        ingredient = Ingredient.objects.get(id=ingredient_id)
        ingredient.check_reorder()  # เช็คว่าเป็นวัตถุดิบที่ต้องเติมหรือไม่
        return redirect('manage_ingredients')  # รีเฟรชหน้าเมื่อทำการอัปเดต
    return render(request, 'manage_ingredients.html', {'ingredients': ingredients,'page_obj': page_obj})

@login_required
def add_ingredient(request):
    store = request.user.member_profile.store
    if request.method == 'POST':
        form = IngredientOrderForm(request.POST)
        if form.is_valid():
            ingredient = form.save(commit=False)
            ingredient.store = store
            ingredient.save()
            return redirect('manage_ingredients')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
    return redirect('manage_ingredients')
def edit_ingredient(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    if request.method == 'POST':
        form = IngredientOrderForm(request.POST, instance=ingredient)
        if form.is_valid():
            form.save()
            return redirect('manage_ingredients')
    else:
        form = IngredientOrderForm(instance=ingredient)
    return render(request, 'manage_ingredient_edit.html', {'form': form, 'ingredient': ingredient})
@login_required
def delete_ingredient(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    ingredient.delete()
    member = request.user.member_profile
    if member.role == 'employee':
        return redirect('manage_ingredients_employee')
    return redirect('manage_ingredients')

@login_required
def manage_product_ingredients(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # รับร้านค้าที่เกี่ยวข้องกับผู้ใช้ที่เข้าสู่ระบบ
    store = request.user.member_profile.store

    # รับ ProductIngredients ทั้งหมดสำหรับผลิตภัณฑ์ที่กำหนด
    ingredients = ProductIngredient.objects.filter(product=product)

    # รับผลิตภัณฑ์ที่เป็นของร้านค้าสำหรับเมนูแบบเลื่อนลงที่เลือก
    products = Product.objects.filter(store=store)
    ingredients_list = Ingredient.objects.filter(store=store)

    if request.method == "POST":
        # สร้างแบบฟอร์มด้วยข้อมูล POST
        form = ProductIngredientForm(request.POST)

        # ตรวจสอบให้แน่ใจว่าผลิตภัณฑ์ที่เลือกมาจากร้านค้าที่ถูกต้อง
        form.instance.product = product

        if form.is_valid():
            form.save()
            return redirect('manage_product_ingredients', product_id=product.id)
        else:
            messages.error(request, 'เกิดข้อผิดพลาดในการเพิ่มส่วนผสมของสินค้า')

    else:
        # เริ่มต้นแบบฟอร์มเปล่า
        form = ProductIngredientForm()

    return render(request, 'manage_product_ingredients.html', {
        'product': product,
        'form': form,
        'ingredients': ingredients,
        'products': products,
        'ingredients_list': ingredients_list,
    })


@login_required
def delete_product_ingredient(request, ingredient_id):
    ingredient = get_object_or_404(ProductIngredient, id=ingredient_id)
    ingredient.delete()
    return redirect('manage_product_ingredients', product_id=ingredient.product.id)


@login_required
def edit_product_ingredient(request, ingredient_id):
    # รับร้านค้าของผู้ใช้ที่เข้าสู่ระบบ
    store = request.user.member_profile.store
    product_ingredient = get_object_or_404(ProductIngredient, id=ingredient_id)

    # ดึงผลิตภัณฑ์ทั้งหมดจากร้านค้าของผู้ใช้ (เกี่ยวข้องกับส่วนผสมของสินค้า)
    products = Product.objects.filter(store=store)
    ingredients_list = Ingredient.objects.filter(store=store)

    # ประมวลผลคำขอ POST เพื่ออัปเดต ProductIngredient
    if request.method == 'POST':
        form = ProductIngredientForm(request.POST, instance=product_ingredient)

        if form.is_valid():
            form.save()  # บันทึก ProductIngredient ที่อัปเดตแล้ว
            return redirect('manage_product_ingredients', product_id=product_ingredient.product.id)
        else:
            messages.error(request, 'เกิดข้อผิดพลาดในการอัปเดตส่วนผสมของสินค้า')
    else:
        # หากไม่ใช่คำขอ POST ให้เริ่มต้นแบบฟอร์มด้วยข้อมูลที่มีอยู่
        form = ProductIngredientForm(instance=product_ingredient)

    return render(request, 'edit_product_ingredient.html', {
        'form': form,
        'product_ingredient': product_ingredient,
        'products': products,
        'ingredients_list': ingredients_list,
    })


@login_required
def manage_product_ingredient_list(request):
    # รับร้านค้าที่เกี่ยวข้องกับผู้ใช้ที่เข้าสู่ระบบ
    store = request.user.member_profile.store

    # ดึงข้อมูลผลิตภัณฑ์ทั้งหมดที่เป็นของร้านค้าของผู้ใช้
    product_ingredients_list = Product.objects.filter(store=store)

    # สำหรับแต่ละผลิตภัณฑ์ให้นำส่วนผสมมาด้วย
    product_with_ingredients = []
    for product in product_ingredients_list:
        # รับส่วนผสมที่เกี่ยวข้องกับผลิตภัณฑ์นี้
        ingredients = ProductIngredient.objects.filter(product=product)
        product_with_ingredients.append({
            'product': product,
            'ingredients': ingredients
        })

    return render(request, 'manage_product_ingredient_list.html', {
        'product_with_ingredients': product_with_ingredients
    })

@login_required
def manage_promotions(request):
    store = request.user.member_profile.store
    search_query = request.GET.get('search', '')  # รับคำค้นหาจากฟอร์ม
    promotions = Promotion.objects.filter(store=store)

    # ค้นหาสินค้าที่เกี่ยวข้องกับโปรโมชั่น
    if search_query:
        products = Product.objects.filter(store=store, product_name__icontains=search_query)
    else:
        products = Product.objects.filter(store=store)

        # Paginate products
    paginator = Paginator(products, 10)  # Show 10 products per page
    page_number = request.GET.get('page')  # Get the current page number
    page_obj = paginator.get_page(page_number)

    return render(request, 'manage_promotions.html', {
        'promotions': promotions,
        'products': page_obj.object_list,  # Pass the products for the current page
        'page_obj': page_obj,  # Pass the paginator object for the template
        'search_query': search_query,  # Pass the search query
    })
@login_required
def add_promotion(request):
    if request.method == 'POST':
        form = PromotionForm(request.POST)
        if form.is_valid():
            promotion = form.save(commit=False)
            promotion.store = request.user.member_profile.store
            promotion.save()
            form.save()
            return redirect('manage_promotions')
    else:
        form = PromotionForm()
    return render(request, 'add_promotion.html', {'form': form})

@login_required
def update_product_promotion(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    store = request.user.member_profile.store

    if request.method == 'POST':
        promotion_id = request.POST.get('promotion')

        if promotion_id:
            promotion = get_object_or_404(Promotion, id=promotion_id, store=store)
            if promotion.is_active():
                product.promotion = promotion
                messages.success(request, 'อัปเดตโปรโมชันสำเร็จแล้ว!')
            else:
                messages.error(request, 'โปรโมชั่นที่เลือกไม่ทำงาน')
        else:
            product.promotion = None
            messages.success(request, 'ลบโปรโมชันสำเร็จแล้ว!')

        product.save()

    return redirect('manage_promotions')

@login_required
def edit_promotion(request, promotion_id):
    promotion = get_object_or_404(Promotion, id=promotion_id, store=request.user.member_profile.store)
    if request.method == 'POST':
        form = PromotionForm(request.POST, instance=promotion)
        if form.is_valid():
            form.save()
            messages.success(request, 'แก้ไขโปรโมชันสำเร็จแล้ว!')
            return redirect('manage_promotions')
    else:
        form = PromotionForm(instance=promotion)
    return render(request, 'edit_promotion.html', {'form': form})

@login_required
def delete_promotion(request, promotion_id):
    promotion = get_object_or_404(Promotion, id=promotion_id, store=request.user.member_profile.store)
    promotion.delete()
    messages.success(request, 'ลบโปรโมชันสำเร็จแล้ว!')
    return redirect('manage_promotions')

@csrf_exempt
@login_required
def edit_category(request, category_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_name = data.get('name')
            category = get_object_or_404(Category, id=category_id, store=request.user.member_profile.store)
            category.name = new_name
            category.save()
            return JsonResponse({'status': 'success', 'message': 'แก้ไขหมวดหมู่สำเร็จ'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
@login_required
def delete_category(request, category_id):
    if request.method == 'DELETE':
        try:
            category = get_object_or_404(Category, id=category_id, store=request.user.member_profile.store)
            category.delete()
            return JsonResponse({'status': 'success', 'message': 'ลบหมวดหมู่สำเร็จ'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def manage_employees(request):
    store = request.user.member_profile.store
    search_query = request.GET.get('search', '')
    employees = Member.objects.filter(store=store)

    # Get top sales employee
    top_sales_employee = employees.annotate(
        total_sales=Sum('user__handled_orders__total_price')
    ).order_by('-total_sales').first()

    # Get top orders employee
    top_orders_employee = employees.annotate(
        total_orders=Count('user__handled_orders')
    ).order_by('-total_orders').first()

    # Search functionality
    if search_query:
        employees = employees.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    paginator = Paginator(employees, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'search_query': search_query,
        'page_obj': page_obj,
        'employees': page_obj.object_list,
        'top_sales_employee': top_sales_employee,
        'top_orders_employee': top_orders_employee,
    }

    return render(request, 'manage_employees.html', context)
@login_required
def employee_performance(request, employee_id):
    employee = get_object_or_404(Member, id=employee_id)
    store = request.user.member_profile.store
    orders = Order.objects.filter(employee=employee.user, store=store)
    range = request.GET.get('range', 'today')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if range == 'today':
        orders = orders.filter(created_at__date=timezone.now().date())
    elif range == 'week':
        start_of_week = timezone.now() - timedelta(days=timezone.now().weekday())
        orders = orders.filter(created_at__date__gte=start_of_week.date())
    elif range == 'month':
        orders = orders.filter(created_at__month=timezone.now().month)
    elif range == 'custom' and start_date and end_date:
        orders = orders.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

    total_orders = orders.count()
    total_revenue = orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    average_order_value = orders.aggregate(Avg('total_price'))['total_price__avg'] or 0

    data = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'average_order_value': average_order_value,
    }
    return JsonResponse(data)

@login_required
def top_employees(request):
    store = request.user.member_profile.store
    filter_range = request.GET.get('filter', 'today')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    employees = Member.objects.filter(store=store)

    # กรองออเดอร์ของพนักงานในร้านค้า
    orders = Order.objects.filter(employee__in=employees.values_list('user', flat=True), store=store)

    if filter_range == 'today':
        orders = orders.filter(created_at__date=timezone.now().date())

    elif filter_range == 'week':
        start_of_week = timezone.now() - timedelta(days=timezone.now().weekday())
        orders = orders.filter(created_at__date__gte=start_of_week.date())

    elif filter_range == 'month':
        orders = orders.filter(created_at__month=timezone.now().month)

    elif filter_range == 'custom' and start_date and end_date:
        orders = orders.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

    # คำนวณยอดขายและจำนวนออเดอร์ของแต่ละพนักงาน
    employees = employees.annotate(
        total_sales=Sum('user__handled_orders__total_price', filter=Q(user__handled_orders__in=orders), default=0),
        total_orders=Count('user__handled_orders', filter=Q(user__handled_orders__in=orders), distinct=True)
    ).order_by('-total_sales')[:5]

    data = [
        {
            'name': f'{employee.user.first_name} {employee.user.last_name}',
            'total_sales': employee.total_sales or 0,
            'total_orders': employee.total_orders or 0
        }
        for employee in employees
    ]

    return JsonResponse(data, safe=False)
@login_required
def add_employee(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])  # ตั้งรหัสผ่าน
            user.save()

            # สร้างโปรไฟล์พนักงาน (Member)
            Member.objects.create(
                user=user,
                role=form.cleaned_data['role'],
                store=request.user.member_profile.store
            )
            messages.success(request, 'เพิ่มพนักงานสำเร็จแล้ว!')
            return redirect('manage_employees')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ถูกต้อง')
    else:
        form = EmployeeForm()

    return render(request, 'add_employee.html', {'form': form})

@login_required
def edit_employee(request, employee_id):
    employee = get_object_or_404(Member, id=employee_id)
    user = employee.user

    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            if form.cleaned_data['password']:
                user.set_password(form.cleaned_data['password'])
            user.save()
            employee.role = form.cleaned_data['role']
            employee.save()
            messages.success(request, 'อัพเดตข้อมูลพนักงานสำเร็จแล้ว!')
            return redirect('manage_employees')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ถูกต้อง')
    else:
        form = EmployeeForm(instance=user)

    return render(request, 'edit_employee.html', {'form': form, 'employee': employee})

@login_required
def delete_employee(request, employee_id):
    employee = get_object_or_404(Member, id=employee_id)
    employee.user.delete()  # ลบ user พร้อมกัน
    employee.delete()
    messages.success(request, 'ลบพนักงานสำเร็จแล้ว!')
    return redirect('manage_employees')

@login_required
def home_employee(request):
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
    customer_points = 0  # ตัวแปรในการเก็บคะแนนลูกค้า

    if order:
        total_price = sum(detail.price for detail in order.order_details.all())
        total_quantity = sum(detail.quantity for detail in order.order_details.all())

        # ดึงคะแนนของลูกค้า
        if order.customer_phone:
            try:
               # ดึงข้อมูลลูกค้าจากเบอร์โทร
                customer = customerMember.objects.get(phone=order.customer_phone)
                customer_points = customer.points # ดึงคะแนนลูกค้า
            except customerMember.DoesNotExist:
                customer_points = 0  # ถ้าไม่พบข้อมูลลูกค้าให้คะแนนเป็น 0

    # ฟอร์มสำหรับกรอกข้อมูลลูกค้า
    form = CustomerInfoForm()

    # ส่งข้อมูล options_list ในแต่ละ product ไปยัง template
    for product in page_obj:
        # ใช้ .all() เพื่อดึงข้อมูล options ที่เชื่อมโยงกับ product
        product.options_list = [option.name for option in product.options.all()] if product.options.exists() else []
        product.discounted_price = product.get_discounted_price()  # คำนวณราคาสินค้าหลังหักส่วนลด

    # ส่งข้อมูลไปยัง template
    return render(request, 'home_staff.html', {
        'page_obj': page_obj,
        'query': query,
        'category': category,
        'categories': categories,  # ส่งหมวดหมู่ทั้งหมด
        'order': order if order else None,  # ส่งคำสั่งซื้อล่าสุดไปยัง template
        'total_price': total_price,
        'total_quantity': total_quantity,
        'customer_points': customer_points,  # ส่งคะแนนลูกค้าไปยัง template
        'form': form,  # ส่งฟอร์มข้อมูลลูกค้า
    })

@login_required
def Order1_staff(request):
    # รับคำสั่งซื้อทั้งหมดที่มีสถานะการชำระเงินเป็น 'สำเร็จ'
    store = request.user.member_profile.store
    orders = Order.objects.filter(
        payment__payment_status='Success',
        store=store,
        status='Pending'
    )

    # Pagination: กำหนดจำนวนคำสั่งซื้อต่อหน้า
    page_number = request.GET.get('page', 1)
    paginator = Paginator(orders, 10)  # แสดง 10 คำสั่งซื้อต่อหน้า
    page_obj = paginator.get_page(page_number)

    # คำนวณปริมาณรวมสำหรับการสั่งซื้อแต่ละครั้ง
    for order in page_obj:
        total_quantity = sum(detail.quantity for detail in order.order_details.all())
        order.total_quantity = total_quantity

    return render(request, 'Order_staff.html', {'page_obj': page_obj})

@login_required
def History_Order_staff(request):
    store = request.user.member_profile.store  # รับร้านค้าที่เกี่ยวข้องกับผู้ใช้ที่เข้าสู่ระบบ
    search_query = request.GET.get('search', '')  # รับคำค้นหา (รหัสคำสั่งซื้อ ชื่อลูกค้า ฯลฯ)
    date_filter = request.GET.get('date_filter', '')  # รับตัวกรองวันที่ที่เลือก (เช่น 'today', 'this_week')

    ## เริ่มต้นเงื่อนไขตัวกรองสำหรับคำสั่งซื้อที่สำเร็จ
    orders = Order.objects.filter(store=store, payment__payment_status='Success')  # ค่าเริ่มต้น: คำสั่งซื้อที่สำเร็จทั้งหมด

    # ใช้ตัวกรองวันที่
    if date_filter == 'today':
        today = datetime.today().date()
        orders = orders.filter(created_at__date=today)
    elif date_filter == 'this_week':
        today = datetime.today().date()
        start_of_week = today - timedelta(days=today.weekday())  #เริ่มต้นสัปดาห์
        end_of_week = start_of_week + timedelta(days=6)  # ท้ายสัปดาห์
        orders = orders.filter(created_at__date__range=[start_of_week, end_of_week])
    elif date_filter == 'this_month':
        today = datetime.today()
        first_day_of_month = today.replace(day=1)  # รับวันแรกของเดือนปัจจุบัน
        last_day_of_month = (first_day_of_month.replace(month=first_day_of_month.month + 1) - timedelta(days=1))  #วันสุดท้ายของเดือน
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
                pass  # ไม่ต้องทำอะไรถ้าเกิดข้อผิดพลาด

    # ใช้คำค้นหา
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(order_details__product__product_name__icontains=search_query) |
            Q(status__icontains=search_query)
        ).distinct()

    # การแบ่งหน้า
    page_number = request.GET.get('page', 1)
    paginator = Paginator(orders, 10)  # แบ่งคำสั่งซื้อเป็นหน้าละ 10 รายการ
    page_obj = paginator.get_page(page_number)

    return render(request, 'History_Order_staff.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'date_filter': date_filter,

    })

@login_required
def Member1_staff(request):
    # ดึงข้อมูลการตั้งค่าแต้ม
    points_config = PointsConfig.objects.first()  # รับการตั้งค่าแต้มแรกที่พบ
    form = PointsConfigForm(instance=points_config)
    store = request.user.member_profile.store

    #จัดการการค้นหาลูกค้า
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
    paginator = Paginator(customers, 10)  # Show 10 employees per page
    page_number = request.GET.get('page')  # Get the current page number
    page_obj = paginator.get_page(page_number)
    evaluation_data = []
    if request.method == "POST":
        form = CustomerMemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member.store = store
            member.save()
            messages.success(request, "สมาชิกใหม่ถูกเพิ่มแล้ว!")
            return redirect("member_employee")
        else:
            messages.error(request, "กรุณากรอกข้อมูลให้ครบถ้วน")

    return render(request, 'Member1_staff.html', {
        'customers': page_obj.object_list,
        'form': form,
        'search_query': search_query,
        'page_obj': page_obj,
    })

@login_required
def edit_member_staff(request, member_id):
    customer = get_object_or_404(customerMember, id=member_id)
    if request.method == 'POST':
        form = CustomerMemberForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'ข้อมูลสมาชิกถูกอัพเดตแล้ว!')
            return redirect('member_employee')
    else:
        form = CustomerMemberForm(instance=customer)

    return render(request, 'edit_member_staff.html', {'form': form, 'customer': customer})

@login_required
def manage_ingredients_staff(request):
    store = request.user.member_profile.store
    ingredients = Ingredient.objects.filter(store=store)  # ดึงข้อมูลวัตถุดิบทั้งหมดจากฐานข้อมูล
    page_number = request.GET.get('page', 1)
    paginator = Paginator(ingredients, 10)  # Show 10 ingredients per page
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        ingredient_id = request.POST.get('ingredient_id')  # รับ ingredient_id ที่ส่งมาจากฟอร์ม
        ingredient = Ingredient.objects.get(id=ingredient_id)
        ingredient.check_reorder()  # เช็คว่าเป็นวัตถุดิบที่ต้องเติมหรือไม่
        return redirect('manage_ingredients_employee')  # รีเฟรชหน้าเมื่อทำการอัปเดต
    return render(request, 'manage_ingredients_staff.html', {'ingredients': ingredients,'page_obj': page_obj})

def edit_ingredient_staff(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    if request.method == 'POST':
        form = IngredientOrderForm(request.POST, instance=ingredient)
        if form.is_valid():
            form.save()
            return redirect('manage_ingredients_employee')
    else:
        form = IngredientOrderForm(instance=ingredient)
    return render(request, 'manage_ingredient_edit_staff.html', {'form': form, 'ingredient': ingredient})

@login_required
def add_ingredient_staff(request):
    store = request.user.member_profile.store
    if request.method == 'POST':
        form = IngredientOrderForm(request.POST)
        if form.is_valid():
            ingredient = form.save(commit=False)
            ingredient.store = store
            ingredient.save()
            return redirect('manage_ingredients_employee')
        else:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
    return redirect('manage_ingredients_employee')

@login_required
@csrf_exempt
def PayNow_staff(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)
        store = request.user.member_profile.store

        if request.method == 'POST':
            form = CustomerInfoForm(request.POST)

            if form.is_valid():
                # รับข้อมูลลูกค้าจากแบบฟอร์ม
                customer_name = form.cleaned_data['customer_name']
                customer_phone = form.cleaned_data['customer_phone']

                #อัพเดทออเดอร์พร้อมข้อมูลลูกค้า
                order.customer_name = customer_name
                order.customer_phone = customer_phone
                order.employee = request.user
                order.store = store
                order.save()
                # เปลี่ยนเส้นทางไปยังหน้าการชำระเงิน
                return redirect('payment_employee', order_id=order.id)

            else:
                messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')

        else:
            # หากไม่ใช่คำขอ POST ให้แสดงแบบฟอร์มด้วยข้อมูลลูกค้าที่มีอยู่ (ถ้ามี)
            form = CustomerInfoForm(initial={
                'customer_name': order.customer_name,
                'customer_phone': order.customer_phone,
            })

    except Exception as e:
        print(f"Error occurred while processing the payment: {e}")
        messages.error(request, 'เกิดข้อผิดพลาดในการชำระเงิน กรุณาลองใหม่อีกครั้ง')
        return redirect('home_employee')

    return render(request, 'Payment_staff.html', {
        'form': form,
        'order': order,
    })

@transaction.atomic
@login_required
def PayMent_staff(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    store = request.user.member_profile.store
    total_order_price = Decimal(0)
    order_details = []

    for detail in order.order_details.all():
        selected_options = detail.order_detail_options.all()
        total_option_price = sum(opt.option.price * opt.quantity for opt in selected_options)
        unit_price = detail.product.get_discounted_price() + total_option_price
        total_item_price = unit_price * detail.quantity

        order_details.append({
            'product_name': detail.product.product_name,
            'quantity': detail.quantity,
            'unit_price': unit_price,
            'total_item_price': total_item_price,
            'options': [
                {'name': opt.option.name, 'price': opt.option.price, 'quantity': opt.quantity}
                for opt in selected_options
            ],
        })
        total_order_price += total_item_price

    points_config = PointsConfig.objects.first()
    points_earned = 0
    discount = Decimal(0)

    if points_config:
        points_earned = int(total_order_price * points_config.points_per_baht)

    customer = None
    customer_points = 0

    if order.customer_phone:
        try:
            customer = customerMember.objects.get(phone=order.customer_phone)
            customer_points = customer.points
        except customerMember.DoesNotExist:
            customer = None

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        amount_paid = Decimal(request.POST.get('amount_paid', 0))
        points_used = int(request.POST.get('points_used', '0'))  # ✅ ดึงค่าที่ใช้แต้มออกมา

        if customer and points_config and points_used > 0:
            if points_used > customer.points:
                messages.error(request, 'แต้มสะสมของคุณไม่เพียงพอ กรุณาลองใหม่')
                return redirect('payment_employee', order_id=order.id)

            # ✅ คำนวณส่วนลดจากแต้ม
            discount = Decimal(points_used) / points_config.points_to_baht
            total_order_price -= discount
            if total_order_price < 0:
                total_order_price = 0  # ป้องกันราคาติดลบ

            # ✅ บันทึกแต้มที่ใช้ลงฐานข้อมูล
            order.points_used = points_used  # ✅ อัปเดตแต้มที่ใช้
            order.total_price = total_order_price  # ✅ อัปเดตราคาสุทธิหลังลดแต้ม
            order.save()  # ✅ บันทึกคำสั่งซื้ออัปเดตลงฐานข้อมูล

            # ✅ อัปเดตแต้มลูกค้า
            customer.points -= points_used
            customer.save()

        # ✅ คำนวณเงินทอน
        change = amount_paid - total_order_price

        # ✅ บันทึกการชำระเงิน
        Payment.objects.create(
            order=order,
            amount=total_order_price,  # ✅ ใช้ราคาที่ลดแล้ว
            payment_method=payment_method,
            payment_status='Success',
            store=store,
        )

        # ✅ ให้แต้มลูกค้าเพิ่มจากการสั่งซื้อ
        if customer:
            customer.points += points_earned
            customer.save()

        return redirect('order_employee')

    return render(request, 'Payment_staff.html', {
        'order': order,
        'order_details': order_details,
        'total_order_price': total_order_price,
        'discount': discount,
        'discounted_price': total_order_price,
        'points_earned': points_earned,
        'customer_points': customer_points,
        'points_config': points_config,
    })
