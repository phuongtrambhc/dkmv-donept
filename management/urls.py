from django.urls import path
from . import views

app_name = 'management'

urlpatterns = [
    path('statistical_reports/',views.statistical_reports, name = 'statistical_reports'),
    path('export_orders/', views.export_orders_xls, name='export_orders'),
    # path('orders/', views.order_list, name='order_list'),



]



