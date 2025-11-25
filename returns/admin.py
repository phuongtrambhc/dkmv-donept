from django.contrib import admin
from .models import Return, ReturnItem, ReturnImage

class ReturnItemInline(admin.TabularInline):
   model = ReturnItem
   extra = 0
   readonly_fields = ['order_product', 'quantity', 'get_refund_amount']

   def get_refund_amount(self, obj):
       return f"${obj.get_refund_amount()}"

   get_refund_amount.short_description = 'Refund Amount'

class ReturnImageInline(admin.TabularInline):
   model = ReturnImage
   extra = 0
   readonly_fields = ['image', 'uploaded_at']

@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
   list_display = ['return_number', 'order', 'user', 'status', 'return_type', 'refund_amount', 'created_at']
   list_filter = ['status', 'return_type', 'reason', 'created_at']
   search_fields = ['return_number', 'order__order_number', 'user__email']
   readonly_fields = ['return_number', 'created_at', 'updated_at', 'approved_at', 'completed_at']
   inlines = [ReturnItemInline, ReturnImageInline]

   fieldsets = (
       ('Basic Information', {
           'fields': ('return_number', 'order', 'user', 'return_type', 'reason', 'description')
       }),
       ('Status', {
           'fields': ('status', 'refund_amount', 'admin_note', 'processed_by')
       }),
       ('Timestamps', {
           'fields': ('created_at', 'updated_at', 'approved_at', 'completed_at')
       }),
   )

