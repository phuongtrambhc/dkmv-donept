from django.contrib import admin
from .models import Category


class CategoryAdmin(admin.ModelAdmin):
    # Trường sẽ hiển thị trong bảng list
    list_display = ('category_name', 'slug')

    # Tự động sinh slug từ category_name
    prepopulated_fields = {'slug': ('category_name',)}


# Đăng ký model với admin
admin.site.register(Category, CategoryAdmin)

