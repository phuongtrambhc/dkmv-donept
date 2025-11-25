# coupon/urls.py
from django.urls import path
from . import views

app_name = 'coupons'

urlpatterns = [
    path("apply/", views.apply_coupon, name="apply_coupon"),
    path("remove/", views.remove_coupon, name="remove_coupon"),
    path('my_coupons/', views.my_coupons_view, name='my_coupons'),

    path('', views.coupon_list, name='coupon_list'),
    path('create/', views.coupon_create, name='coupon_create'),
    path('/<int:pk>/edit/', views.coupon_update, name='coupon_update'),
    path('/<int:pk>/delete/', views.coupon_delete, name='coupon_delete'),
    path("/<int:pk>/", views.coupon_detail, name="coupon_detail"),  # 👈 NEW
]

