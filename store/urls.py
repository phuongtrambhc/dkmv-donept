from django.urls import path
from . import views

urlpatterns = [
    # STAFF – CATEGORY
    path('staff/categories/', views.staff_category_list, name='staff_category_list'),
    path('staff/categories/add/', views.staff_category_add, name='staff_category_add'),
    path('staff/categories/<int:id>/edit/', views.staff_category_edit, name='staff_category_edit'),
    path('staff/categories/<int:id>/delete/', views.staff_category_delete, name='staff_category_delete'),

    # STAFF – PRODUCTS
    path('staff/products/', views.staff_product_list, name='staff_product_list'),
    path('staff/products/add/', views.staff_product_create, name='staff_product_create'),
    path('staff/products/<int:pk>/edit/', views.staff_product_update, name='staff_product_update'),
    path('staff/products/<int:pk>/delete/', views.staff_product_delete, name='staff_product_delete'),

    # STAFF – PRODUCT VARIANTS
    path('staff/products/<int:product_id>/variants/', views.staff_variant_by_product, name='staff_variant_by_product'),
    path('staff/products/<int:product_id>/variants/add/', views.staff_variant_create, name='staff_variant_create'),
    path('staff/variants/<int:variant_id>/edit/', views.staff_variant_update, name='staff_variant_update'),
    path('staff/variants/<int:variant_id>/delete/', views.staff_variant_delete, name='staff_variant_delete'),

    # STORE
    path('', views.store, name='store'),
    path('search/', views.search, name='search'),

    # CATEGORY PAGE
    path('category/<slug:category_slug>/', views.store, name='products_by_category'),

    # AJAX
    path('get-sizes/<int:product_id>/', views.get_sizes, name='get_sizes'),
    # 👉 THÊM URL KIỂM TRA TỒN KHO TRƯỚC KHI ADD TO CART
    path('check-variation-stock/', views.check_variation_stock, name='check_variation_stock'),

    # PRODUCT DETAIL
    path('<slug:category_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),
]