from django.urls import path
from . import views

app_name = 'returns'

urlpatterns = [
   # Customer URLs
   path('create/<str:order_number>/', views.create_return, name='create_return'),
   path('my-returns/', views.my_returns, name='my_returns'),
   path('detail/<str:return_number>/', views.return_detail, name='return_detail'),


   # Admin URLs
   path('admin/list/', views.admin_return_list, name='admin_return_list'),
   path('admin/detail/<str:return_number>/', views.admin_return_detail, name='admin_return_detail'),
   path('admin/approve/<int:return_id>/', views.approve_return, name='approve_return'),
   path('admin/reject/<int:return_id>/', views.reject_return, name='reject_return'),
   path('admin/complete/<int:return_id>/', views.complete_return, name='complete_return'),
]

