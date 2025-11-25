import urllib

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from carts.models import Cart
from .forms import RegistrationForm, UserForm, UserProfileForm
from .models import Account, UserProfile
from orders.models import Order, OrderProduct

from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from coupons.models import Coupon, CouponUsage


#VERIFICATION EMAIL
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage

from carts.views import _cart_id
from carts.models import Cart, CartItem
import requests
from datetime import timedelta
from django.utils import timezone

from django.db.models import Sum, Count, Avg
from store.models import Product
from coupons.models import Coupon  # Thêm dòng này vào phần import


# Create your views here.
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            email = form.cleaned_data.get('email')
            phone_number = form.cleaned_data.get('phone_number')
            password = form.cleaned_data.get('password')
            username = email.split('@')[0]
            user = Account.objects.create_user(first_name=first_name, last_name=last_name, email=email,username=username, password=password)
            user.phone_number = phone_number
            user.save()

            # Create a user profile
            profile = UserProfile()
            profile.user_id = user.id
            profile.profile_picture = 'default/default-user.png'
            profile.save()

            # USER ACTIVATION
            current_site = get_current_site(request)
            mail_subject = 'Activate your account.'
            message = render_to_string('accounts/account_activation_email.html', {
                'user' : user,
                'domain' : current_site,
                'uid'   : urlsafe_base64_encode(force_bytes(user.pk)),
                'token' :   default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()
            #messages.success(request, 'Thank you for registering. We have sent you an activation link to your email address. Please check your email to activate your account.')
            return redirect('/accounts/login/?command=verification&email='+email)
    else:
        form = RegistrationForm()
    context = {
        'form': form
    }
    return render(request, 'accounts/register.html', context)

def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user =  auth.authenticate(email=email, password=password)

        if user is not None:
            try:
                cart = Cart.objects.get(cart_id=_cart_id(request))
                is_cart_item_exists = CartItem.objects.filter(cart = cart).exists()
                if is_cart_item_exists:
                    cart_item = CartItem.objects.filter(cart=cart)

                    #Getting product variation by cart_id
                    product_variation = []
                    for item in cart_item:
                        variation = item.variations.all()
                        product_variation.append(list(variation))

                    # Getting the cart items from the user to access his product variations
                    cart_item = CartItem.objects.filter(user=user)
                    ex_var_list = []
                    id = []
                    for item in cart_item:
                        existing_variation = item.variations.all()
                        ex_var_list.append(list(existing_variation))
                        id.append(item.id)

                    #product_variation = [1, 2, 3, 4, 6]
                    #ex_var_list = [4, 6, 3, 5]

                    for pr in product_variation:
                        if pr in ex_var_list:
                            index = ex_var_list.index(pr)
                            item_id = id[index]
                            item = CartItem.objects.get(id=item_id)
                            item.quantity += 1
                            item.user = user
                            item.save()
                        else:
                            cart_item = CartItem.objects.filter(cart=cart)
                            for item in cart_item:
                                item.user = user
                                item.save()
            except:
                pass
            auth.login(request, user)
            messages.success(request, 'You are logged in')
            url = request.META.get('HTTP_REFERER')
            try:
                query = requests.utils.urlparse(url).query

                # next=/cart/checkout/
                params = dict(x.split('=') for x in query.split('&'))
                if 'next' in params:
                    nextPage = params['next']
                    return redirect(nextPage)
            except:
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid login credentials')
            return redirect('login')

    return render(request, 'accounts/login.html')

@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'You are logged out.')
    return redirect('login')

def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Congratulation! Your account has been activated.')
        return redirect('login')
    else:
        messages.error(request, 'Activation link is invalid!')
        return redirect('register')


@login_required(login_url='login')
def dashboard(request):
    user = request.user

    # Kiểm tra role của user
    if user.role == 'admin' or user.role == 'staff' or user.is_superuser:        # ADMIN/STAFF DASHBOARD
        # Thống kê tổng quan
        total_orders = Order.objects.filter(is_ordered=True).count()
        total_revenue = Order.objects.filter(is_ordered=True).aggregate(Sum('order_total'))['order_total__sum'] or 0
        total_customers = Account.objects.filter(role='customer').count()
        total_products = Product.objects.all().count()

        # ======= THÊM THỐNG KÊ RETURNS =======
        try:
            from returns.models import Return
            total_returns = Return.objects.all().count()
            pending_returns = Return.objects.filter(status='Pending').count()
        except:
            total_returns = 0
            pending_returns = 0
        # =====================================

        # Đơn hàng gần đây
        recent_orders = Order.objects.filter(is_ordered=True).order_by('-created_at')[:10]

        # Đơn hàng chờ xử lý (status = 'New' hoặc tương tự)
        pending_orders = Order.objects.filter(is_ordered=True, status='New').count()

        context = {
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'total_customers': total_customers,
            'total_products': total_products,
            'recent_orders': recent_orders,
            'pending_orders': pending_orders,
            'total_returns': total_returns,
            'pending_returns': pending_returns,

        }
        return render(request, 'accounts/admin_dashboard.html', context)


    elif user.role == 'customer':
        # CUSTOMER DASHBOARD

        try:
            orders = Order.objects.filter(user_id=request.user.id, is_ordered=True).order_by('-created_at')
            orders_count = orders.count()
            userprofile = UserProfile.objects.get(user_id=request.user.id)
            # Returns

            try:
                from returns.models import Return
                returns_count = Return.objects.filter(user=request.user).count()
                pending_returns = Return.objects.filter(user=request.user, status='Pending').count()

            except:
                returns_count = 0
                pending_returns = 0

            context = {

                'orders_count': orders_count,
                'userprofile': userprofile,
                'orders': orders,
                'returns_count': returns_count,
                'pending_returns': pending_returns,

            }

        except UserProfile.DoesNotExist:

            context = {
                'orders_count': 0,
                'userprofile': None,
                'returns_count': 0,
                'pending_returns': 0,

            }

        return render(request, 'accounts/customer_dashboard.html', context)

    else:
        # Trường hợp khác về trang chủ
        return redirect('home')

def forgotPassword(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__exact=email)

            #Reset password
            current_site = get_current_site(request)
            mail_subject = 'Reset Your Password'
            message = render_to_string('accounts/reset_password_email.html', {
                'user' : user,
                'domain' : current_site,
                'uid'   : urlsafe_base64_encode(force_bytes(user.pk)),
                'token' :   default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()

            messages.success(request, 'Password reset email has been sent to your email.')
            return redirect('login')


        else:
            messages.error(request, 'Account does not exist')
            return redirect('forgotPassword')

    return render(request, 'accounts/forgotPassword.html')

def resetpassword_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.success(request, 'Password reset your password.')
        return redirect('resetPassword')
    else:
        messages.error(request, 'This link has been expired.')
        return redirect('login')


def resetPassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        comfirm_password = request.POST['confirm_password']

        if password == comfirm_password:
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request, 'Your password has been updated.')
            return redirect('login')

        else:
            messages.error(request, 'Passwords do not match! Please try again.')
            return redirect('resetPassword')
    else:
        return render(request, 'accounts/resetPassword.html')

@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')

    # Add can_return flag to each order
    for order in orders:
        days_since_order = (timezone.now() - order.created_at).days
        order.can_return = (order.status == 'Completed' and days_since_order <= 14)
        order.days_since_order = days_since_order

    context = {
        'orders': orders,
    }
    return render(request, 'accounts/my_orders.html', context)

@login_required(login_url='login')
def edit_profile(request):
    userprofile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=userprofile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('edit_profile')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=userprofile)
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'userprofile': userprofile,
    }
    return render(request, 'accounts/edit_profile.html', context)

@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST['current_password']
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']

        user = Account.objects.get(username__exact=request.user.username)

        if new_password == confirm_password:
            success = user.check_password(current_password)
            if success:
                user.set_password(new_password)
                user.save()
                # auth.logout(request)
                messages.success(request, 'Password updated successfully.')
                return redirect('change_password')
            else:
                messages.error(request, 'Please enter valid current password')
                return redirect('change_password')
        else:
            messages.error(request, 'Password does not match!')
            return redirect('change_password')
    return render(request, 'accounts/change_password.html')


@login_required(login_url='login')
def order_detail(request, order_number):
   user = request.user


   try:
       # Lấy đơn hàng theo order_number
       order = Order.objects.get(order_number=order_number, is_ordered=True)


       # Kiểm tra quyền: chỉ admin/staff hoặc chủ đơn hàng mới xem được
       if user.role not in ['admin', 'staff'] and order.user != user:
           return redirect('dashboard')


       # Nếu admin/staff cập nhật trạng thái
       if request.method == 'POST' and user.role in ['admin', 'staff']:


           new_status = request.POST.get('status')


           # Kiểm tra status hợp lệ theo model Order.STATUS
           valid_statuses = dict(Order.STATUS).keys()


           if new_status in valid_statuses:
               order.status = new_status
               order.save()
               messages.success(request, f'Order status updated to {new_status}')
               return redirect('order_detail', order_number=order_number)
           else:
               messages.error(request, "Invalid status selected.")


       # Lấy các sản phẩm trong đơn hàng
       order_items = OrderProduct.objects.filter(order=order)

       # Tính subtotal
       subtotal = sum(item.product_price * item.quantity for item in order_items)

       context = {
           'order': order,
           'order_items': order_items,
           'subtotal': subtotal,
       }
       return render(request, 'orders/order_detail.html', context)


   except Order.DoesNotExist:
       return redirect('dashboard')


@login_required(login_url='login')
def order_management(request):
   user = request.user

   if user.role not in ['admin', 'staff']:
       messages.error(request, 'You do not have permission to access order management.')
       return redirect('dashboard')

   # 🔥 Chỉ lấy đơn có tick xanh (is_ordered=True)
   orders = Order.objects.filter(
       is_ordered=True
   ).order_by('-created_at')

   context = {
       'orders': orders,
   }
   return render(request, 'accounts/order_management.html', context)

# ========================================
# ADMIN CUSTOMER MANAGEMENT VIEWS
# ========================================


@login_required(login_url='login')
def admin_customer_list(request):
   """Danh sách khách hàng cho admin/staff"""
   # Kiểm tra quyền admin hoặc staff
   if request.user.role not in ['admin', 'staff']:
       messages.error(request, 'Bạn không có quyền truy cập trang này.')
       return redirect('dashboard')


   # CHỈ LẤY KHÁCH HÀNG (role='customer')
   customers = Account.objects.filter(role='customer').order_by('-date_joined')


   # Search functionality
   search_query = request.GET.get('search', '')
   if search_query:
       from django.db.models import Q
       customers = customers.filter(
           Q(email__icontains=search_query) |
           Q(first_name__icontains=search_query) |
           Q(last_name__icontains=search_query) |
           Q(phone_number__icontains=search_query)
       )


   # Filter by status only (BỎ FILTER ROLE)
   status_filter = request.GET.get('status', '')
   if status_filter == 'active':
       customers = customers.filter(is_active=True)
   elif status_filter == 'inactive':
       customers = customers.filter(is_active=False)


   # Pagination
   from django.core.paginator import Paginator
   paginator = Paginator(customers, 10)
   page_number = request.GET.get('page')
   page_obj = paginator.get_page(page_number)


   # Statistics - CHỈ CUSTOMER
   total_customers = Account.objects.filter(role='customer').count()
   active_customers = Account.objects.filter(role='customer', is_active=True).count()
   inactive_customers = Account.objects.filter(role='customer', is_active=False).count()


   context = {
       'page_obj': page_obj,
       'search_query': search_query,
       'status_filter': status_filter,
       'total_customers': total_customers,
       'active_customers': active_customers,
       'inactive_customers': inactive_customers,
   }


   return render(request, 'accounts/customer_list.html', context)




@login_required(login_url='login')
def customer_detail(request, customer_id):
   """Chi tiết khách hàng - CHỈ THÔNG TIN CÁ NHÂN"""
   # Kiểm tra quyền admin hoặc staff
   if request.user.role not in ['admin', 'staff']:
       messages.error(request, 'Bạn không có quyền truy cập trang này.')
       return redirect('dashboard')


   # Lấy thông tin khách hàng - CHỈ CUSTOMER
   customer = get_object_or_404(Account, id=customer_id, role='customer')


   # Lấy UserProfile
   try:
       profile = UserProfile.objects.get(user=customer)
   except UserProfile.DoesNotExist:
       profile = None


   context = {
       'customer': customer,
       'profile': profile,
       'is_admin': request.user.role == 'admin',
   }


   return render(request, 'accounts/customer_detail.html', context)




@login_required(login_url='login')
def toggle_customer_status(request, customer_id):
   """Khóa/Mở khóa tài khoản - CHỈ ADMIN"""
   if request.user.role != 'admin':
       messages.error(request, 'Chỉ Admin mới có quyền khóa/mở khóa tài khoản!')
       return redirect('customer_detail', customer_id=customer_id)


   if request.method == 'POST':
       customer = get_object_or_404(Account, id=customer_id, role='customer')
       customer.is_active = not customer.is_active
       customer.save()


       status = "mở khóa" if customer.is_active else "khóa"
       messages.success(request, f'Đã {status} tài khoản {customer.email}')


   return redirect('customer_detail', customer_id=customer_id)




@login_required(login_url='login')
def delete_customer(request, customer_id):
   """Xóa tài khoản - CHỈ ADMIN"""
   if request.user.role != 'admin':
       messages.error(request, 'Chỉ Admin mới có quyền xóa tài khoản!')
       return redirect('customer_detail', customer_id=customer_id)


   if request.method == 'POST':
       customer = get_object_or_404(Account, id=customer_id, role='customer')


       # Kiểm tra có đơn hàng không
       has_orders = Order.objects.filter(user=customer, is_ordered=True).exists()


       if has_orders:
           messages.warning(request,
                            f'Không thể xóa khách hàng {customer.email} vì đã có đơn hàng. Hãy khóa tài khoản thay thế.')
           return redirect('customer_detail', customer_id=customer_id)


       email = customer.email
       customer.delete()
       messages.success(request, f'Đã xóa tài khoản {email} thành công!')
       return redirect('admin_customer_list')


   return redirect('customer_detail', customer_id=customer_id)

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


