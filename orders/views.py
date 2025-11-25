from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.utils import timezone

from django.contrib.auth.decorators import login_required

from carts.models import CartItem
from store.models import ProductVariant
from coupons.models import Coupon
from .forms import OrderForm
from .models import Order, Payment, OrderProduct

import datetime


# ==========================================================
# PLACE ORDER
# ==========================================================
def place_order(request, total=0, quantity=0):
    current_user = request.user

    # ========================================
    # CHẶN ADMIN/STAFF ĐẶT HÀNG
    # ========================================
    if current_user.role in ['admin', 'staff']:
        messages.error(request, 'Admin/Staff không thể đặt hàng. Vui lòng tạo tài khoản khách hàng riêng.')
        return redirect('dashboard')
    # ========================================

    cart_items = CartItem.objects.filter(user=current_user)
    if not cart_items.exists():
        return redirect('store')

    # TÍNH TỔNG TIỀN
    for item in cart_items:
        total += item.product.price * item.quantity
        quantity += item.quantity

    # COUPON
    coupon_percent = int(request.session.get("coupon_percent", 0))
    coupon_id = request.session.get("coupon_id")
    coupon_code = None

    discount_amount = 0
    if coupon_id:
        try:
            coupon_obj = Coupon.objects.get(id=coupon_id)
            coupon_code = coupon_obj.code
            discount_amount = round(total * (coupon_percent / 100), 2)
        except Coupon.DoesNotExist:
            pass

    sub_total_after_discount = total - discount_amount
    VAT = round(sub_total_after_discount * 0.08, 2)
    grand_total = round(sub_total_after_discount + VAT, 2)

    # SUBMIT FORM
    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            order = Order()
            order.user = current_user
            order.first_name = form.cleaned_data['first_name']
            order.last_name = form.cleaned_data['last_name']
            order.phone = form.cleaned_data['phone']
            order.email = form.cleaned_data['email']
            order.address_line_1 = form.cleaned_data['address_line_1']
            order.address_line_2 = form.cleaned_data['address_line_2']
            order.country = form.cleaned_data['country']
            order.state = form.cleaned_data['state']
            order.city = form.cleaned_data['city']
            order.order_note = form.cleaned_data['order_note']

            order.order_total = grand_total
            order.VAT = VAT
            order.discount = discount_amount
            order.coupon = coupon_code
            order.ip = request.META.get('REMOTE_ADDR')
            order.save()

            # ORDER NUMBER
            current_date = datetime.date.today().strftime("%Y%m%d")
            order.order_number = current_date + str(order.id)
            order.save()

            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'discount_amount': discount_amount,
                'sub_total_after_discount': sub_total_after_discount,
                'VAT': VAT,
                'grand_total': grand_total,
            }
            return render(request, 'orders/confirm_cod_payment.html', context)

    return redirect('checkout')



# ==========================================================
# CONFIRM COD PAYMENT
# ==========================================================
def confirm_cod_payment(request):
    if request.method != 'POST':
        return redirect('checkout')

    current_user = request.user
    order_number = request.POST.get("order_number")

    try:
        order = Order.objects.get(user=current_user, order_number=order_number, is_ordered=False)
    except Order.DoesNotExist:
        return redirect('home')

    cart_items = CartItem.objects.filter(user=current_user)
    if not cart_items.exists():
        return redirect('store')

    # TẠO PAYMENT
    payment = Payment.objects.create(
        user=current_user,
        payment_id=f"COD-{order_number}",
        payment_method="COD",
        amount_paid=order.order_total,
        status="Pending",
    )

    # GẮN PAYMENT
    order.payment = payment
    order.is_ordered = True
    order.save()

    # CHUYỂN CART → ORDERPRODUCT
    for item in cart_items:
        op = OrderProduct.objects.create(
            order=order,
            payment=payment,
            user=current_user,
            product=item.product,
            quantity=item.quantity,
            product_price=item.product.price,
            variant=item.variant,   # 🔥 LƯU BIẾN THỂ
            ordered=True
        )

        # 🔥 TRỪ STOCK TRONG BIẾN THỂ
        pv = item.variant
        pv.stock -= item.quantity
        if pv.stock < 0:
            pv.stock = 0
        pv.save()

    # XOÁ CART
    cart_items.delete()

    return redirect(
        f'/orders/order_complete/?order_number={order.order_number}&payment_id={payment.payment_id}'
    )



# ==========================================================
# ORDER COMPLETE
# ==========================================================
@login_required(login_url='login')
def order_complete(request):
    order_number = request.GET.get("order_number")
    payment_id = request.GET.get("payment_id")

    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        payment = Payment.objects.get(payment_id=payment_id)
        ordered_products = OrderProduct.objects.filter(order=order)

        subtotal = sum(item.product_price * item.quantity for item in ordered_products)

        return render(request, "orders/order_complete.html", {
            "order": order,
            "payment": payment,
            "ordered_products": ordered_products,
            "subtotal": subtotal,
        })

    except:
        return redirect("home")



# ==========================================================
# ORDER DETAIL
# ==========================================================
@login_required(login_url='login')
def order_detail(request, order_number):
   user = request.user


   try:
       # Lấy đơn hàng theo order_number
       order = Order.objects.get(order_number=order_number, is_ordered=True)


       # Kiểm tra quyền: chỉ admin/staff hoặc chủ đơn hàng mới xem được
       if user.role not in ['admin', 'staff'] and order.user != user:
           return redirect('dashboard')


       # Xử lý POST request để cập nhật status (chỉ admin/staff)
       if request.method == 'POST' and user.role in ['admin', 'staff']:
           new_status = request.POST.get('status')
           if new_status in dict(Order.STATUS):
               order.status = new_status
               order.save()
               messages.success(request, f'Order status updated to {new_status}')
               return redirect('order_detail', order_number=order_number)


       # Lấy các sản phẩm trong đơn hàng
       order_items = OrderProduct.objects.filter(order=order)


       # Tính subtotal
       subtotal = 0
       for item in order_items:
           subtotal += item.product_price * item.quantity

       #Add can_return flag
       days_since_order = (timezone.now() - order.created_at).days
       can_return = (order.status == 'Completed' and days_since_order <= 14)

       context = {
           'order': order,
           'order_items': order_items,
           'subtotal': subtotal,
           'can_return': can_return,
           'days_since_order': days_since_order,
       }
       return render(request, 'orders/order_detail.html', context)


   except Order.DoesNotExist:
       return redirect('dashboard')

