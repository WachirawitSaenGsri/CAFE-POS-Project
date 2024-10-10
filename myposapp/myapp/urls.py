#myapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('home/', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('home/', views.Menu, name='manage_products'),  # เปลี่ยน 'menu/' เป็น 'manage_products'
    path('order/', views.Order1, name='manage_orders'),  # เปลี่ยน 'order/' เป็น 'manage_orders'
    path('payment/', views.PayMent, name='manage_customers'),  # เปลี่ยน 'payment/' เป็น 'manage_customers'
    path('marketing/', views.Marketing, name='Marketing'),  # เปลี่ยน 'marketing/' เป็น 'sales_report'
    path('inventory/', views.inventory, name='inventory'),  # กำหนดให้ 'inventory/' ใช้กับ inventory view
    path('history/', views.History_Order, name='History_Order'),  # เปลี่ยน 'history/' เป็น 'settings'
    path('member/', views.Member1, name='member'),
    path('Addmenu/', views.Addmenu, name='addmenu'),
    #path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('add_to_order/', views.add_to_order, name='add_to_order'),  # เพิ่มเส้นทางสำหรับเพิ่มสินค้าใน order
    path('update_order_detail/', views.update_order_detail, name='update_order_detail'),  # เพิ่มเส้นทางสำหรับอัปเดต order detail
    path('delete_order_detail/', views.delete_order_detail, name='delete_order_detail'),  # เพิ่มเส้นทางสำหรับลบ order detail
]
