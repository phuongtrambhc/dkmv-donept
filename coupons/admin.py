from django.contrib import admin
from django import forms
from .models import Coupon, CouponUsage

class CouponAdminForm(forms.ModelForm):
   class Meta:
       model = Coupon
       fields = "__all__"


   def clean(self):
       cleaned = super().clean()


       applies_to = cleaned.get("applies_to")
       categories = cleaned.get("categories")
       discount = cleaned.get("discount")
       valid_from = cleaned.get("valid_from")
       valid_to = cleaned.get("valid_to")
       min_purchase_amount = cleaned.get("min_purchase_amount")
       max_usage_count = cleaned.get("max_usage_count")
       max_usage_per_customer = cleaned.get("max_usage_per_customer")


       errors = []


       # 1. Bắt buộc category
       if applies_to == "CATEGORY" and (not categories or categories.count() == 0):
           errors.append(
               forms.ValidationError(
                   "Bạn chọn 'CATEGORY' thì phải chọn ít nhất 1 ngành hàng."
               )
           )


       # 2. Ngày hợp lệ
       if valid_from and valid_to and valid_from >= valid_to:
           errors.append(
               forms.ValidationError(
                   "Ngày bắt đầu phải nhỏ hơn ngày kết thúc."
               )
           )


       # 3. Discount từ 1–70 (%)
       if discount is not None and not (1 <= discount <= 70):
           errors.append(
               forms.ValidationError(
                   "Phần trăm giảm giá phải nằm trong khoảng 1% đến 70%."
               )
           )


       # 4. Đơn tối thiểu ≥ 0
       if min_purchase_amount is not None and min_purchase_amount < 0:
           errors.append(
               forms.ValidationError(
                   "Giá trị đơn hàng tối thiểu phải ≥ 0."
               )
           )


       # 5. Tổng lượt dùng ≥ 0
       if max_usage_count is not None and max_usage_count < 0:
           errors.append(
               forms.ValidationError(
                   "Giới hạn tổng số lần sử dụng phải ≥ 0."
               )
           )


       # 6. Lượt / khách ≥ 0
       if max_usage_per_customer is not None and max_usage_per_customer < 0:
           errors.append(
               forms.ValidationError(
                   "Giới hạn số lần sử dụng trên mỗi khách phải ≥ 0."
               )
           )


       # ❗❗ NOW WE ACTUALLY RAISE THE ERRORS!
       if errors:
           raise forms.ValidationError(errors)


       return cleaned


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
   form = CouponAdminForm


   list_display = (
       "code",
       "discount",
       "applies_to",
       "min_purchase_amount",
       "max_usage_count",
       "max_usage_per_customer",
       "valid_from",
       "valid_to",
       "active",
   )
   list_filter = (
       "active",
       "applies_to",
       "valid_from",
       "valid_to",
   )
   search_fields = ("code", "applies_to")
   filter_horizontal = ("categories",)


   fieldsets = (
       ("Thông tin cơ bản", {
           "fields": ("code", "active")
       }),
       ("Thời gian hiệu lực", {
           "fields": ("valid_from", "valid_to")
       }),
       ("Giảm giá & điều kiện", {
           "fields": (
               "discount",
               "max_discount_amount",
               "min_purchase_amount",
           )
       }),
       ("Giới hạn sử dụng", {
           "fields": (
               "max_usage_count",
               "max_usage_per_customer",
           )
       }),
       ("Phạm vi áp dụng", {
           "fields": ("applies_to", "categories")
       }),
   )


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
   list_display = ('id', 'coupon', 'user', 'order_id', 'used_count')
   search_fields = ("user__email", "user__username", "coupon__code")
   list_filter = ("coupon",)


