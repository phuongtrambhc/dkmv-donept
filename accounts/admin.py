from django.contrib import admin
from .models import Account, UserProfile
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html


class AccountAdmin(UserAdmin):
    # Các trường sẽ hiển thị trong bảng list
    list_display = ('email', 'first_name', 'last_name', 'username',
                    'last_login', 'is_active', 'is_admin', 'date_joined')

    # Các liên kết trong bảng list để click vào
    list_display_links = ('email', 'first_name', 'last_name')

    # Các trường chỉ đọc
    readonly_fields = ('last_login', 'date_joined')

    # Sắp xếp theo ngày tạo (mới nhất lên đầu)
    ordering = ('-date_joined',)

    # Các tùy chọn khác, giữ trống nếu không cần
    list_filter = ()
    filter_horizontal = ()
    fieldsets = ()

class UserProfileAdmin(admin.ModelAdmin):
    def thumbnail(self, object):
        return format_html('<img src="{}" width="30" style="border-radius:50%;">'.format(object.profile_picture.url))
    thumbnail.short_description = 'Profile Picture'
    list_display = ('thumbnail', 'user', 'city', 'state', 'country')

admin.site.register(Account, AccountAdmin)
admin.site.register(UserProfile, UserProfileAdmin)

# Register your models here.
