#myapp/urls.py
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('home/', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('home/', views.Menu, name='menu'),
    path('order/', views.Order1, name='order'),
    path('payment/<int:order_id>/', views.PayMent, name='payment'),
    path('marketing/', views.Marketing, name='Marketing'),
    path('inventory/', views.inventory, name='inventory'),
    path('history/', views.History_Order, name='History_Order'),
    path('member/', views.Member1, name='member'),
    path('addmenu/', views.Addmenu, name='addmenu'),
    #path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('add_to_order/', views.add_to_order, name='add_to_order'),  # เพิ่มเส้นทางสำหรับเพิ่มสินค้าใน order
    path('update_order_detail/', views.update_order_detail, name='update_order_detail'),
    path('delete_order_detail/', views.delete_order_detail, name='delete_order_detail'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('Payment/', views.PayNow, name='PayNow'),
    path('add_product/', views.add_product, name='add_product'),
    path('edit_product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('delete_product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('add_category/', views.add_category, name='add_category'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
