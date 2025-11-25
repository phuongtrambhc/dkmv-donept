# coupons/views.py
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum


from .models import Coupon, CouponUsage
from .forms import CouponCodeForm
from carts.models import CartItem, Cart
from carts.views import _cart_id
from coupons.admin import CouponAdminForm


# Lấy cart theo user hoặc session
def _get_cart_items(request):
   if request.user.is_authenticated:
       return CartItem.objects.filter(
           user=request.user, is_active=True
       ).select_related("product", "product__category")


   cart = Cart.objects.get(cart_id=_cart_id(request))
   return CartItem.objects.filter(
       cart=cart, is_active=True
   ).select_related("product", "product__category")




# ÁP DỤNG COUPON
def apply_coupon(request):
   if request.method != "POST":
       return redirect("cart")


   form = CouponCodeForm(request.POST)
   if not form.is_valid():
       messages.error(request, "Vui lòng nhập mã hợp lệ.")
       return redirect("cart")


   # ✅ Lấy đúng string code
   code = form.cleaned_data.get("code", "").strip()
   now = timezone.now()


   # 1. Tìm coupon
   try:
       coupon = Coupon.objects.get(code__iexact=code)
   except Coupon.DoesNotExist:
       request.session.pop("coupon_id", None)
       request.session.pop("coupon_percent", None)
       messages.error(request, f"Mã “{code}” không tồn tại.")
       return redirect("cart")


   status = coupon.get_status()


   if status == "expired":
       messages.error(request, f"Mã “{coupon.code}” đã hết hạn sử dụng.")
       return redirect("cart")


   if status == "upcoming":
       messages.warning(request, f"Mã “{coupon.code}” chưa đến thời gian áp dụng.")
       return redirect("cart")


   if status == "inactive":
       messages.error(request, f"Mã “{coupon.code}” hiện đang tắt, không thể áp dụng.")
       return redirect("cart")


   # 4. Cart items & phạm vi áp dụng
   cart_items = _get_cart_items(request)
   eligible_subtotal = coupon.eligible_subtotal(cart_items)


   if eligible_subtotal <= 0:
       messages.warning(
           request,
           f"Mã “{coupon.code}” không áp dụng cho sản phẩm trong giỏ."
       )
       return redirect("cart")


   # 5. Đơn tối thiểu
   if coupon.min_purchase_amount > 0 and eligible_subtotal < coupon.min_purchase_amount:
       messages.warning(
           request,
           f"Đơn hàng cần đạt tối thiểu {coupon.min_purchase_amount:,.0f}đ "
           "cho sản phẩm được áp mã."
       )
       return redirect("cart")


   # 6. Giới hạn số lần sử dụng (toàn hệ thống + mỗi khách)
   if request.user.is_authenticated:
       user = request.user


       # 6.1. Giới hạn mỗi khách
       if coupon.max_usage_per_customer > 0:
           user_used = CouponUsage.objects.filter(
               coupon=coupon,
               user=user,
           ).count()
           if user_used >= coupon.max_usage_per_customer:
               messages.warning(
                   request,
                   f"Bạn đã dùng hết số lần cho phép của mã “{coupon.code}”."
               )
               return redirect("cart")


       # 6.2. Giới hạn tổng số lần trên toàn hệ thống
       if coupon.max_usage_count > 0:
           total_used = CouponUsage.objects.filter(
               coupon=coupon
           ).count()
           if total_used >= coupon.max_usage_count:
               messages.warning(
                   request,
                   f"Mã “{coupon.code}” đã đạt giới hạn số lần sử dụng."
               )
               return redirect("cart")
   else:
       # Khách chưa đăng nhập: chỉ kiểm tra giới hạn tổng (nếu muốn)
       if coupon.max_usage_count > 0:
           total_used = CouponUsage.objects.filter(
               coupon=coupon
           ).count()
           if total_used >= coupon.max_usage_count:
               messages.warning(
                   request,
                   f"Mã “{coupon.code}” đã đạt giới hạn số lần sử dụng."
               )
               return redirect("cart")


   # --> Nếu tất cả OK → lưu vào session
   request.session["coupon_id"] = coupon.id
   request.session["coupon_percent"] = coupon.discount


   messages.success(
       request,
       f"Áp dụng mã “{coupon.code}” thành công: giảm {coupon.discount}%"
   )
   return redirect("cart")




# XÓA COUPON
def remove_coupon(request):
   request.session.pop("coupon_id", None)
   request.session.pop("coupon_percent", None)
   messages.info(request, "Đã bỏ mã giảm giá.")
   return redirect("cart")




# TRANG "COUPON CỦA TÔI"
@login_required(login_url='login')
def my_coupons_view(request):
   user = request.user


   # Lấy tất cả coupon, để model tự quyết định trạng thái (active / upcoming / expired / inactive)
   all_coupons = Coupon.objects.all().order_by('-valid_to')


   visible_coupons = []


   for coupon in all_coupons:
       status = coupon.get_status()  # 'active', 'upcoming', 'expired', 'inactive'


       # ❌ Bỏ qua những mã đã hết hạn hoặc đang tắt
       if status in ("expired", "inactive"):
           continue


       # ✅ Giữ lại cả "active" và "upcoming"
       # Kiểm tra giới hạn tổng số lần sử dụng (toàn hệ thống)
       if coupon.max_usage_count > 0:
           total_used = CouponUsage.objects.filter(coupon=coupon).count()
           if total_used >= coupon.max_usage_count:
               continue  # đã dùng hết lượt phát hành


       # Kiểm tra giới hạn theo từng khách hàng
       if coupon.max_usage_per_customer > 0:
           user_used = CouponUsage.objects.filter(
               coupon=coupon,
               user=user,
           ).count()
           if user_used >= coupon.max_usage_per_customer:
               continue  # user này đã dùng hết lượt cho mã này


       visible_coupons.append(coupon)


   visible_coupons.sort(key=lambda c: c.valid_to)


   context = {
       "coupons": visible_coupons,
   }
   return render(request, "accounts/my_coupons.html", context)

@staff_member_required
def coupon_list(request):
    now = timezone.now()
    coupons = Coupon.objects.all().order_by('-valid_to')

    # Dashboard numbers
    total_coupons = coupons.count()
    active_coupons = coupons.filter(active=True, valid_from__lte=now, valid_to__gte=now).count()
    expired_coupons = coupons.filter(valid_to__lt=now).count()
    upcoming_coupons = coupons.filter(valid_from__gt=now).count()
    total_usage = CouponUsage.objects.aggregate(total=Sum("used_count"))["total"] or 0

    # THÊM PHẦN NÀY — Thống kê usage cho từng coupon
    for c in coupons:
        c.used_total = CouponUsage.objects.filter(coupon=c).aggregate(
            used=Sum("used_count")
        )["used"] or 0

    context = {
        "now": now,
        "coupons": coupons,
        "total_coupons": total_coupons,
        "active_coupons": active_coupons,
        "expired_coupons": expired_coupons,
        "upcoming_coupons": upcoming_coupons,
        "total_usage": total_usage,
    }
    return render(request, 'coupons/coupon_list.html', context)

@staff_member_required
def coupon_create(request):
    """Tạo Coupon mới"""
    if request.method == 'POST':
        form = CouponAdminForm (request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tạo mã giảm giá mới thành công!')
            return redirect('coupons:coupon_list')
        else:
            # Nếu form không hợp lệ, messages.error sẽ hiển thị lỗi form
            messages.error(request, 'Đã có lỗi xảy ra. Vui lòng kiểm tra lại dữ liệu.')
    else:
        form =CouponAdminForm()

    context = {'form': form, 'title': 'Tạo Mã Giảm Giá Mới'}
    return render(request, 'coupons/coupon_form.html', context)

@staff_member_required
def coupon_update(request, pk):
    """Cập nhật Coupon đã tồn tại"""
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == 'POST':
        form = CouponAdminForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cập nhật mã giảm giá "{coupon.code}" thành công!')
            return redirect('coupons:coupon_list')
        else:
            messages.error(request, 'Đã có lỗi xảy ra. Vui lòng kiểm tra lại dữ liệu.')
    else:
        form = CouponAdminForm(instance=coupon)

    context = {'form': form, 'title': f'Chỉnh sửa Mã Giảm Giá: {coupon.code}'}
    return render(request, 'coupons/coupon_form.html', context)

@staff_member_required
def coupon_delete(request, pk):
    """Xóa Coupon (dùng POST method)"""
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == 'POST':
        coupon.delete()
        messages.success(request, f'Đã xóa mã giảm giá "{coupon.code}" thành công.')

    # Chuyển hướng về trang list sau khi xóa hoặc nếu không phải POST
    return redirect('coupons:coupon_list')

@staff_member_required
def coupon_detail(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)

    now = timezone.now()

    # Status tính toán
    if coupon.valid_to < now:
        status_label = "expired"      # đã hết hạn
    elif coupon.valid_from > now:
        status_label = "upcoming"     # chưa bắt đầu
    elif coupon.active:
        status_label = "active"       # đang hoạt động
    else:
        status_label = "inactive"     # tắt thủ công

    # Thống kê lượt sử dụng của mã này
    usage_qs = CouponUsage.objects.filter(coupon=coupon)
    total_used = usage_qs.aggregate(total=Sum("used_count"))["total"] or 0
    distinct_users = usage_qs.values("user").distinct().count()
    remain = None
    if coupon.max_usage_count > 0:
        remain = coupon.max_usage_count - total_used


    context = {
        "coupon": coupon,
        "total_used": total_used,
        "distinct_users": distinct_users,
        "status_label": status_label,
        "remain": remain,
    }
    return render(request, "coupons/coupon_detail.html", context)

