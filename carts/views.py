from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from store.models import Product, ProductVariant
from .models import Cart, CartItem
from coupons.forms import CouponCodeForm
from coupons.models import Coupon




# ============================================================
# SESSION CART ID
# ============================================================
def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart


# ============================================================
# ADD TO CART (dùng ProductVariant)
# ============================================================
def add_cart(request, product_id):
    # ===== CHẶN ADMIN/STAFF =====
    if request.user.is_authenticated and request.user.role in ['admin', 'staff']:
        messages.error(request, 'Admin/Staff không thể sử dụng chức năng giỏ hàng.')
        return redirect('dashboard')
    # ============================

    product = get_object_or_404(Product, id=product_id)

    color = request.POST.get("color")
    size = request.POST.get("size")

    if not color or not size:
        messages.error(request, "Vui lòng chọn màu và size.")
        return redirect(request.META.get("HTTP_REFERER"))

    # Tìm biến thể theo màu & size (không phân biệt hoa thường)
    try:
        variant = ProductVariant.objects.get(
            product=product,
            color__iexact=color,
            size__iexact=size,
        )
    except ProductVariant.DoesNotExist:
        messages.error(request, "Biến thể không tồn tại.")
        return redirect(request.META.get("HTTP_REFERER"))


    # Hết hàng
    if variant.stock <= 0:
        messages.warning(request, "Biến thể này đã hết hàng.")
        return redirect(request.META.get("HTTP_REFERER"))

    # User đã đăng nhập
    if request.user.is_authenticated:
        user = request.user

        try:
            cart_item = CartItem.objects.get(
                user=user, product=product, variant=variant
            )
            if cart_item.quantity < variant.stock:
                cart_item.quantity += 1
                cart_item.save()
            else:
                messages.warning(request, "Không đủ hàng trong kho.")
        except CartItem.DoesNotExist:
            CartItem.objects.create(
                user=user, product=product, variant=variant, quantity=1
            )

        return redirect("cart")

    # User chưa đăng nhập (session cart)
    cart_id = _cart_id(request)
    cart, _ = Cart.objects.get_or_create(cart_id=cart_id)

    try:
        cart_item = CartItem.objects.get(
            cart=cart, product=product, variant=variant
        )
        if cart_item.quantity < variant.stock:
            cart_item.quantity += 1
            cart_item.save()
        else:
            messages.warning(request, "Không đủ hàng trong kho.")
    except CartItem.DoesNotExist:
        CartItem.objects.create(
            cart=cart, product=product, variant=variant, quantity=1
        )

    return redirect("cart")

# ============================================================
# REMOVE 1 UNIT
# ============================================================
def remove_cart(request, product_id, cart_item_id):
    # ===== CHẶN ADMIN/STAFF =====
    if request.user.is_authenticated and request.user.role in ['admin', 'staff']:
        messages.error(request, 'Admin/Staff không thể sử dụng chức năng giỏ hàng.')
        return redirect('dashboard')
    # ============================

    product = get_object_or_404(Product, id=product_id)

    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(id=cart_item_id, user=request.user)

        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)

        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()

    except:
        pass

    return redirect("cart")



# ============================================================
# REMOVE ENTIRE ITEM
# ============================================================
def remove_cart_item(request, product_id, cart_item_id):
    # ===== CHẶN ADMIN/STAFF =====
    if request.user.is_authenticated and request.user.role in ['admin', 'staff']:
        messages.error(request, 'Admin/Staff không thể sử dụng chức năng giỏ hàng.')
        return redirect('dashboard')
    # ============================

    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(id=cart_item_id, user=request.user)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)

        cart_item.delete()
    except:
        pass

    return redirect("cart")



# ============================================================
# GET CART ITEMS
# ============================================================
def _get_cart_items_qs(request):
    if request.user.is_authenticated:
        return CartItem.objects.filter(user=request.user, is_active=True)

    cart = Cart.objects.get(cart_id=_cart_id(request))
    return CartItem.objects.filter(cart=cart, is_active=True)



# ============================================================
# CART PAGE
# ============================================================
def cart(request, total=0, quantity=0):

    try:
        cart_items = _get_cart_items_qs(request)

        for ci in cart_items:
            total += ci.product.price * ci.quantity
            quantity += ci.quantity

        coupon_id = request.session.get("coupon_id")
        coupon_percent = int(request.session.get("coupon_percent", 0))
        discount_amount = 0

        if coupon_id and coupon_percent:
            try:
                coupon = Coupon.objects.get(pk=coupon_id, active=True)
                eligible_subtotal = coupon.eligible_subtotal(cart_items)
                discount_amount = round(eligible_subtotal * (coupon_percent / 100), 2)
            except Coupon.DoesNotExist:
                pass

        discounted_subtotal = max(total - discount_amount, 0)
        VAT = round(discounted_subtotal * 0.08, 2)
        grand_total = round(discounted_subtotal + VAT, 2)

    except:
        cart_items = []
        discount_amount = 0
        VAT = 0
        grand_total = 0

    context = {
        "total": total,
        "quantity": quantity,
        "cart_items": cart_items,
        "discount_amount": discount_amount,
        "discount_percent": request.session.get("coupon_percent", 0),
        "VAT": VAT,
        "grand_total": grand_total,
        "coupon_form": CouponCodeForm(),
    }

    return render(request, "store/cart.html", context)



# ============================================================
# CHECKOUT PAGE
# ============================================================
@login_required(login_url="login")
def checkout(request, total=0, quantity=0):
    # ===== CHẶN ADMIN/STAFF =====
    if request.user.role in ['admin', 'staff']:
        messages.error(request, 'Admin/Staff không thể đặt hàng. Vui lòng tạo tài khoản khách hàng riêng.')
        return redirect('dashboard')
    # ============================
    cart_items = _get_cart_items_qs(request)

    for ci in cart_items:
        total += ci.product.price * ci.quantity
        quantity += ci.quantity

    coupon_id = request.session.get("coupon_id")
    coupon_percent = int(request.session.get("coupon_percent", 0))
    discount_amount = 0

    if coupon_id and coupon_percent:
        try:
            coupon = Coupon.objects.get(pk=coupon_id, active=True)
            eligible_subtotal = coupon.eligible_subtotal(cart_items)
            discount_amount = round(eligible_subtotal * (coupon_percent / 100), 2)
        except Coupon.DoesNotExist:
            pass

    discounted_subtotal = max(total - discount_amount, 0)
    VAT = round(discounted_subtotal * 0.08, 2)
    grand_total = round(discounted_subtotal + VAT, 2)

    context = {
        "total": total,
        "quantity": quantity,
        "cart_items": cart_items,
        "discount_amount": discount_amount,
        "discount_percent": coupon_percent,
        "VAT": VAT,
        "grand_total": grand_total,
    }

    return render(request, "store/checkout.html", context)

def cart(request, total=0, quantity=0, cart_items=None):
   try:
       cart_items = _get_cart_items_qs(request)


       for ci in cart_items:
           # total là tổng của TẤT CẢ sản phẩm trong giỏ
           total += ci.product.price * ci.quantity
           quantity += ci.quantity


       coupon_id = request.session.get("coupon_id")
       coupon_percent = int(request.session.get("coupon_percent", 0))
       discount_amount = 0
       max_discount = 0  # truyền ra template


       if coupon_id and coupon_percent:
           try:
               coupon = Coupon.objects.get(pk=coupon_id, active=True)


               # Tính tổng phụ đủ điều kiện áp dụng
               eligible_subtotal = coupon.eligible_subtotal(cart_items)


               # Gọi method tính toán đã bao gồm max_discount_amount
               discount_amount = round(
                   coupon.get_discount_value(eligible_subtotal), 2
               )
               max_discount = coupon.max_discount_amount


           except Coupon.DoesNotExist:
               coupon_percent = 0
               max_discount = 0


       discounted_subtotal = max(total - discount_amount, 0)
       VAT = round(0.08 * discounted_subtotal, 2)
       grand_total = round(discounted_subtotal + VAT, 2)


   except Exception:
       # Nếu có lỗi: tránh vỡ page
       cart_items = []
       coupon_percent = 0
       discount_amount = 0
       VAT = 0
       grand_total = 0
       max_discount = 0


   context = {
       "total": total,
       "quantity": quantity,
       "cart_items": cart_items,
       "VAT": VAT,
       "grand_total": grand_total,
       "discount_percent": coupon_percent,
       "discount_amount": discount_amount,
       "max_discount": max_discount,
       "coupon_form": CouponCodeForm(),
   }
   return render(request, "store/cart.html", context)




@login_required(login_url='login')
def checkout(request, total=0, quantity=0, cart_items=None):
   cart_items = _get_cart_items_qs(request)


   for ci in cart_items:
       total += ci.product.price * ci.quantity
       quantity += ci.quantity


   coupon_id = request.session.get("coupon_id")
   coupon_percent = int(request.session.get("coupon_percent", 0))
   discount_amount = 0
   max_discount = 0


   if coupon_id and coupon_percent:
       try:
           coupon = Coupon.objects.get(pk=coupon_id, active=True)
           eligible_subtotal = coupon.eligible_subtotal(cart_items)


           discount_amount = round(
               coupon.get_discount_value(eligible_subtotal), 2
           )
           max_discount = coupon.max_discount_amount


       except Coupon.DoesNotExist:
           coupon_percent = 0
           max_discount = 0


   discounted_subtotal = max(total - discount_amount, 0)
   VAT = round(0.08 * discounted_subtotal, 2)
   grand_total = round(discounted_subtotal + VAT, 2)


   context = {
       "total": total,
       "quantity": quantity,
       "cart_items": cart_items,
       "VAT": VAT,
       "grand_total": grand_total,
       "discount_percent": coupon_percent,
       "discount_amount": discount_amount,
       "max_discount": max_discount,
   }
   return render(request, "store/checkout.html", context)


