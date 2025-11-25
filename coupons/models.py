# coupons/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from category.models import Category
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Coupon(models.Model):
   code = models.CharField(max_length=10, unique=True)
   description=models.TextField(blank=True)
   valid_from = models.DateTimeField()
   valid_to = models.DateTimeField()
   discount = models.IntegerField(
       validators=[MinValueValidator(1), MaxValueValidator(70)]
   )
   active = models.BooleanField(default=False)


   # --- Giới hạn & điều kiện ---
   max_discount_amount = models.PositiveIntegerField(
       default=0,
       help_text="Giá trị giảm giá tối đa (VND). Nếu là 0, giảm giá không bị giới hạn tối đa."
   )
   max_usage_count = models.PositiveIntegerField(
       default=0,
       help_text="Tổng số lần tối đa mã có thể được sử dụng (0: Không giới hạn)."
   )
   max_usage_per_customer = models.PositiveIntegerField(
       default=1,
       help_text="Số lần tối đa mỗi khách hàng (đã đăng nhập) được sử dụng mã."
   )
   min_purchase_amount = models.PositiveIntegerField(
       default=0,
       help_text="Giá trị đơn hàng tối thiểu (trước giảm giá) để áp dụng mã (0: Không yêu cầu)."
   )


   APPLIES_TO_CHOICES = (
       ('ALL', ' TOÀN BỘ '),
       ('CATEGORY', ' NGÀNH HÀNG'),
   )
   applies_to = models.CharField(
       max_length=10,
       choices=APPLIES_TO_CHOICES,
       default='ALL',
       help_text="Phạm vi áp dụng của mã giảm giá."
   )
   categories = models.ManyToManyField(
       Category,
       blank=True,
       help_text="Chọn ngành hàng được áp dụng (chỉ dùng khi applies_to = CATEGORY)."
   )


   class Meta:
       verbose_name = "Coupon Code"


   def __str__(self):
       return self.code


# ============= LOGIC TRẠNG THÁI =============


   def get_status(self) -> str:
       """
       Trả về mã trạng thái nội bộ:
       - 'expired'  : đã hết hạn (valid_to < now)
       - 'upcoming' : chưa tới ngày bắt đầu (valid_from > now)
       - 'inactive' : trong thời gian hiệu lực nhưng active=False
       - 'active'   : trong thời gian hiệu lực và active=True
       """
       now = timezone.now()


       if self.valid_to and self.valid_to < now:
           return "expired"
       if self.valid_from and self.valid_from > now:
           return "upcoming"
       if not self.active:
           return "inactive"
       return "active"


   def get_status_label(self):
       """
       Trả về tuple (text_vi, bootstrap_badge_class)
       dùng cho template hiển thị.
       """
       mapping = {
           "expired": ("Đã hết hạn", "danger"),
           "upcoming": ("Chưa bắt đầu", "warning"),
           "inactive": ("Đang tắt", "secondary"),
           "active": ("Đang hoạt động", "success"),
       }
       return mapping[self.get_status()]


   def is_expired(self) -> bool:
       """Tiện dùng khi chỉ cần check hết hạn hay chưa."""
       return self.get_status() == "expired"


   def is_usable_now(self) -> bool:
       """
       Mã còn trong thời gian hiệu lực *và* đang bật active.
       (Không check điều kiện khác như min_purchase, usage…)
       """
       return self.get_status() == "active"


   # --- Tính tiền giảm ---
   def get_discount_value(self, eligible_subtotal):
       """
       eligible_subtotal: tổng tiền của các item đủ điều kiện.
       Trả về số tiền giảm (đã tính giới hạn max_discount_amount nếu có).
       """
       discount_by_percent = (self.discount / 100) * eligible_subtotal


       if self.max_discount_amount > 0:
           return min(discount_by_percent, self.max_discount_amount)


       return discount_by_percent


   # --- Kiểm tra 1 product có được áp mã không ---
   def applies_to_product(self, product):
       if self.applies_to == 'ALL':
           return True
       return self.categories.filter(pk=getattr(product.category, "pk", None)).exists()


   # --- Tính subtotal đủ điều kiện từ danh sách cart_items ---
   def eligible_subtotal(self, cart_items):
       subtotal = 0
       for ci in cart_items:
           if self.applies_to_product(ci.product):
               subtotal += ci.product.price * ci.quantity
       return subtotal




class CouponUsage(models.Model):
   """
   Lưu lịch sử sử dụng coupon theo từng đơn hàng.
   Mỗi (coupon, user, order_id) chỉ xuất hiện 1 lần.
   """
   coupon = models.ForeignKey(
       Coupon, on_delete=models.CASCADE, related_name='usage_records'
   )
   user = models.ForeignKey(User, on_delete=models.CASCADE)
   order_id = models.CharField(max_length=100)
   used_count = models.PositiveIntegerField(default=0)


   class Meta:
       unique_together = ('coupon', 'user', 'order_id')
       verbose_name = "CouponUsage"


   def __str__(self):
       return f'{self.user.username} used {self.coupon.code} on {self.order_id}'


