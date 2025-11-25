from django.db import models
from django.utils import timezone
from datetime import timedelta
from accounts.models import Account
from orders.models import Order, OrderProduct
from store.models import Product




class Return(models.Model):
   RETURN_STATUS = (
       ('Pending', 'Pending Review'),
       ('Approved', 'Approved'),
       ('Rejected', 'Rejected'),
       ('Processing', 'Processing Refund'),
       ('Completed', 'Completed'),
   )


   RETURN_TYPE = (
       ('Refund', 'Refund Money'),
       ('Exchange', 'Exchange Product'),
   )


   RETURN_REASON = (
       ('Defective', 'Defective/Damaged Product'),
       ('Wrong_Item', 'Wrong Item Received'),
       ('Not_As_Described', 'Not As Described'),
       ('Changed_Mind', 'Changed Mind'),
       ('Size_Issue', 'Size Issue'),
       ('Quality_Issue', 'Quality Issue'),
       ('Other', 'Other'),
   )


   return_number = models.CharField(max_length=20, unique=True)
   order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='returns')
   user = models.ForeignKey(Account, on_delete=models.CASCADE)
   return_type = models.CharField(max_length=20, choices=RETURN_TYPE, default='Refund')
   reason = models.CharField(max_length=50, choices=RETURN_REASON)
   description = models.TextField()
   status = models.CharField(max_length=20, choices=RETURN_STATUS, default='Pending')


   # Admin fields
   admin_note = models.TextField(blank=True, null=True)
   refund_amount = models.FloatField(default=0)
   processed_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='processed_returns')


   # Timestamps
   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)
   approved_at = models.DateTimeField(blank=True, null=True)
   completed_at = models.DateTimeField(blank=True, null=True)


   class Meta:
       ordering = ['-created_at']
       verbose_name = 'Return Request'
       verbose_name_plural = 'Return Requests'


   def __str__(self):
       return f"Return #{self.return_number} - Order #{self.order.order_number}"


   def is_eligible_for_return(self):
       """Check if order is eligible for returns (within 14 days)"""
       if self.order.status != 'Completed':
           return False
       days_since_order = (timezone.now() - self.order.created_at).days
       return days_since_order <= 14


   def calculate_refund(self):
       """Calculate total refund amount"""
       total = 0
       for item in self.items.all():
           total += item.order_product.product_price * item.quantity
       return total




class ReturnItem(models.Model):
   return_request = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='items')
   order_product = models.ForeignKey(OrderProduct, on_delete=models.CASCADE)
   quantity = models.IntegerField(default=1)
   reason_detail = models.TextField(blank=True, null=True)


   def __str__(self):
       return f"{self.order_product.product.product_name} - Qty: {self.quantity}"


   def get_refund_amount(self):
       return self.order_product.product_price * self.quantity




class ReturnImage(models.Model):
   return_request = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='images')
   image = models.ImageField(upload_to='returns/%Y/%m/')
   uploaded_at = models.DateTimeField(auto_now_add=True)


   def __str__(self):
       return f"Image for Return #{self.return_request.return_number}"

