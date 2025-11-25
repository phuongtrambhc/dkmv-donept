import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


from .models import Return, ReturnItem, ReturnImage
from .forms import ReturnRequestForm, ReturnImageForm, AdminReturnActionForm
from orders.models import Order, OrderProduct

# ==================== CUSTOMER VIEWS ====================


@login_required
def create_return(request, order_number):
   """Create returns request for an order"""
   user = request.user


   try:
       order = Order.objects.get(order_number=order_number, user=user, is_ordered=True)
   except Order.DoesNotExist:
       messages.error(request, 'Order not found.')
       return redirect('my_orders')


   # Check if order is eligible for returns
   if order.status != 'Completed':
       messages.error(request, 'Only completed orders can be returned.')
       return redirect('my_orders')


   days_since_order = (timezone.now() - order.created_at).days
   if days_since_order > 14:
       messages.error(request, 'Return period has expired. You can only returns within 14 days of order.')
       return redirect('my_orders')


   # Check if already has pending returns
   if Return.objects.filter(order=order, status='Pending').exists():
       messages.warning(request, 'You already have a pending returns request for this order.')
       return redirect('my_returns')


   if request.method == 'POST':
       form = ReturnRequestForm(request.POST)
       images = request.FILES.getlist('images')
       selected_items = request.POST.getlist('items')


       if not selected_items:
           messages.error(request, 'Please select at least one item to returns.')
           # Re-create form for display
           form = ReturnRequestForm()
       elif len(images) == 0:
           messages.error(request, 'Please upload at least one image.')
           form = ReturnRequestForm(request.POST)
       elif len(images) > 5:
           messages.error(request, 'Maximum 5 images allowed.')
           form = ReturnRequestForm(request.POST)
       elif form.is_valid():
           # Create returns request
           return_request = form.save(commit=False)
           return_request.user = user
           return_request.order = order


           # Generate returns number
           yr = int(datetime.date.today().strftime('%Y'))
           dt = int(datetime.date.today().strftime('%d'))
           mt = int(datetime.date.today().strftime('%m'))
           d = datetime.date(yr, mt, dt)
           current_date = d.strftime("%Y%m%d")
           return_request.save()
           return_number = f"RT{current_date}{return_request.id}"
           return_request.return_number = return_number
           return_request.save()


           # Add returns items
           total_refund = 0
           for item_id in selected_items:
               try:
                   order_product = OrderProduct.objects.get(id=item_id, order=order)
                   quantity = int(request.POST.get(f'quantity_{item_id}', 1))


                   ReturnItem.objects.create(
                       return_request=return_request,
                       order_product=order_product,
                       quantity=quantity
                   )
                   total_refund += order_product.product_price * quantity
               except OrderProduct.DoesNotExist:
                   pass


           # Set refund amount
           return_request.refund_amount = total_refund
           return_request.save()


           # Upload images
           for image in images:
               ReturnImage.objects.create(
                   return_request=return_request,
                   image=image
               )


           # Send email to admin (optional, can comment out for testing)
           try:
               send_return_notification_to_admin(return_request)
           except:
               pass  # Ignore email errors


           messages.success(request, f'Return request #{return_number} has been submitted successfully.')
           return redirect('my_returns')  # Redirect to my_returns instead
       else:
           # Form is invalid
           print("FORM ERRORS:", form.errors)
           messages.error(request, f'Form is invalid: {form.errors}')
   else:
       # GET request
       form = ReturnRequestForm()


   # Get order products
   order_products = OrderProduct.objects.filter(order=order)


   context = {
       'form': form,
       'order': order,
       'order_products': order_products,
       'days_left': 14 - days_since_order,
   }
   return render(request, 'returns/create_return.html', context)






@login_required
def my_returns(request):
   """View customer's returns requests"""
   returns = Return.objects.filter(user=request.user).order_by('-created_at')


   context = {
       'returns': returns,
   }
   return render(request, 'returns/my_returns.html', context)




@login_required
def return_detail(request, return_number):
   """View returns request detail"""
   return_request = get_object_or_404(Return, return_number=return_number)


   # Check permission
   if request.user.role not in ['admin', 'staff'] and return_request.user != request.user:
       messages.error(request, 'You do not have permission to view this returns.')
       return redirect('dashboard')


   context = {
       'return_request': return_request,
   }


   if request.user.role in ['admin', 'staff']:
       return render(request, 'returns/admin_return_detail.html', context)
   else:
       return render(request, 'returns/return_detail.html', context)




# ==================== ADMIN VIEWS ====================


@login_required
def admin_return_list(request):
   """Admin view - List all returns requests"""
   user = request.user


   if user.role not in ['admin', 'staff']:
       messages.error(request, 'Access denied.')
       return redirect('dashboard')


   # Filter by status
   status_filter = request.GET.get('status', 'all')


   if status_filter == 'all':
       returns = Return.objects.all()
   else:
       returns = Return.objects.filter(status=status_filter)


   # Statistics
   pending_count = Return.objects.filter(status='Pending').count()
   approved_count = Return.objects.filter(status='Approved').count()
   rejected_count = Return.objects.filter(status='Rejected').count()
   completed_count = Return.objects.filter(status='Completed').count()


   context = {
       'returns': returns,
       'status_filter': status_filter,
       'pending_count': pending_count,
       'approved_count': approved_count,
       'rejected_count': rejected_count,
       'completed_count': completed_count,
   }
   return render(request, 'returns/admin_return_list.html', context)




@login_required
def admin_return_detail(request, return_number):
   """Admin view - Return request detail with action buttons"""
   user = request.user


   if user.role not in ['admin', 'staff']:
       messages.error(request, 'Access denied.')
       return redirect('dashboard')


   return_request = get_object_or_404(Return, return_number=return_number)


   context = {
       'return_request': return_request,
   }
   return render(request, 'returns/admin_return_detail.html', context)




@login_required
def approve_return(request, return_id):
   """Approve returns request"""
   user = request.user


   if user.role not in ['admin', 'staff']:
       messages.error(request, 'Access denied.')
       return redirect('dashboard')


   return_request = get_object_or_404(Return, id=return_id)


   if request.method == 'POST':
       admin_note = request.POST.get('admin_note', '')
       refund_amount = request.POST.get('refund_amount', return_request.refund_amount)


       return_request.status = 'Approved'
       return_request.admin_note = admin_note
       return_request.refund_amount = float(refund_amount)
       return_request.processed_by = user
       return_request.approved_at = timezone.now()
       return_request.save()


       # Send email to customer
       send_return_status_email(return_request, 'approved')


       messages.success(request, f'Return request #{return_request.return_number} has been approved.')
       return redirect('returns:admin_return_detail', return_number=return_request.return_number)


   return redirect('returns:admin_return_list')




@login_required
def reject_return(request, return_id):
   """Reject returns request"""
   user = request.user


   if user.role not in ['admin', 'staff']:
       messages.error(request, 'Access denied.')
       return redirect('dashboard')


   return_request = get_object_or_404(Return, id=return_id)


   if request.method == 'POST':
       admin_note = request.POST.get('admin_note', '')


       if not admin_note:
           messages.error(request, 'Please provide a reason for rejection.')
           return redirect('returns:admin_return_detail', return_number=return_request.return_number)


       return_request.status = 'Rejected'
       return_request.admin_note = admin_note
       return_request.processed_by = user
       return_request.save()


       # Send email to customer
       send_return_status_email(return_request, 'rejected')


       messages.success(request, f'Return request #{return_request.return_number} has been rejected.')
       return redirect('returns:admin_return_detail', return_number=return_request.return_number)


   return redirect('returns:admin_return_list')




@login_required
def complete_return(request, return_id):
   """Mark returns as completed"""
   user = request.user


   if user.role not in ['admin', 'staff']:
       messages.error(request, 'Access denied.')
       return redirect('dashboard')


   return_request = get_object_or_404(Return, id=return_id)


   if return_request.status != 'Approved':
       messages.error(request, 'Only approved returns can be marked as completed.')
       return redirect('returns:admin_return_detail', return_number=return_request.return_number)


   return_request.status = 'Completed'
   return_request.completed_at = timezone.now()
   return_request.save()


   # Send email to customer
   send_return_status_email(return_request, 'completed')


   messages.success(request, f'Return request #{return_request.return_number} has been completed.')
   return redirect('returns:admin_return_detail', return_number=return_request.return_number)




# ==================== EMAIL FUNCTIONS ====================


def send_return_notification_to_admin(return_request):
   """Send email to admin when new returns request is created"""
   mail_subject = f'New Return Request #{return_request.return_number}'
   message = render_to_string('returns/emails/admin_notification.html', {
       'return_request': return_request,
   })


   # Send to all admin/staff
   from accounts.models import Account
   admin_emails = Account.objects.filter(role__in=['admin', 'staff']).values_list('email', flat=True)


   if admin_emails:
       send_email = EmailMessage(mail_subject, message, to=list(admin_emails))
       send_email.content_subtype = 'html'
       send_email.send()




def send_return_status_email(return_request, status):
   """Send email to customer when returns status changes"""
   if status == 'approved':
       mail_subject = f'Return Request #{return_request.return_number} Approved'
       template = 'returns/emails/approved.html'
   elif status == 'rejected':
       mail_subject = f'Return Request #{return_request.return_number} Rejected'
       template = 'returns/emails/rejected.html'
   elif status == 'completed':
       mail_subject = f'Return Request #{return_request.return_number} Completed'
       template = 'returns/emails/completed.html'
   else:
       return


   message = render_to_string(template, {
       'return_request': return_request,
       'user': return_request.user,
   })


   to_email = return_request.user.email
   send_email = EmailMessage(mail_subject, message, to=[to_email])
   send_email.content_subtype = 'html'
   send_email.send()

