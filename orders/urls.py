# from django.urls import path
# from . import views
#
# urlpatterns = [
#   path('payments/', views.payments, name='payments'),
#   path('order_complete/', views.order_complete, name='order_complete'),
#   path('review_order/', views.review_order, name='review_order'),
#
#
# ]

from django.urls import path
from . import views

urlpatterns = [
    path('place_order/', views.place_order, name='place_order'),
    path('confirm_cod_payment/', views.confirm_cod_payment, name='confirm_cod_payment'),
    path('order_complete/', views.order_complete, name='order_complete'),
    # THÊM DÒNG NÀY
    path('order_complete/', views.order_complete, name='order_complete'),
]


