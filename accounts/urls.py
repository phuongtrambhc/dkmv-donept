from django.contrib import admin
from django.urls import path
from . import views


urlpatterns = [
    path('register/',views.register, name = 'register'),
    path('login/',views.login, name = 'login'),
    path('logout/',views.logout, name = 'logout'),
    path('dashboard/',views.dashboard, name = 'dashboard'),
    path('',views.dashboard, name = 'dashboard'),

    path('activate/<uidb64>/<token>/',views.activate, name = 'activate'),
    path('forgotPassword/',views.forgotPassword, name = 'forgotPassword'),
    path('resetpassword_validate/<uidb64>/<token>/',views.resetpassword_validate, name = 'resetpassword_validate'),
    path('resetPassword/',views.resetPassword, name = 'resetPassword'),

    path('my_orders/', views.my_orders, name='my_orders'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('change_password/', views.change_password, name='change_password'),
    path('order_detail/<str:order_number>/', views.order_detail, name='order_detail'),
    path('order-management/', views.order_management, name='order_management'),

    # ========================================
   # ADMIN CUSTOMER MANAGEMENT URLS
   # ========================================
   path('admin/customers/', views.admin_customer_list, name='admin_customer_list'),
   path('admin/customer/<int:customer_id>/', views.customer_detail, name='customer_detail'),
   path('admin/customer/<int:customer_id>/toggle-status/', views.toggle_customer_status, name='toggle_customer_status'),
   path('admin/customer/<int:customer_id>/delete/', views.delete_customer, name='delete_customer'),
   path('my_coupons/', views.my_coupons_view, name='my_coupons'),

]
