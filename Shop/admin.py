from django.contrib import admin
from django.utils import timezone
from .models import *

# Remove this line - you're registering it twice!
# admin.site.register(Order)

class OrderAdmin(admin.ModelAdmin):
    list_display = ['final_order_id', 'user', 'get_status_display', 'get_payment_status_display', 'created_at', 'total_cost']
    list_filter = ['status', 'payment_method', 'payment_status']
    search_fields = ['final_order_id', 'user__username', 'user__email', 'awb_code']
    readonly_fields = ['created_at', 'packed_at', 'shipped_at', 'out_for_delivery_at',
                      'delivered_at', 'canceled_at', 'return_requested_at', 
                      'return_approved_at', 'returned_at', 'refunded_at',  # ← Add it here
                      'razorpay_order_id', 'razorpay_payment_id', 
                      'shiprocket_order_id', 'shiprocket_shipment_id', 
                      'awb_code', 'courier_name']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('user', 'address', 'final_order_id', 'total_cost', 'payment_method', 'payment_status')
        }),
        ('Payment Details', {
            'fields': ('razorpay_order_id', 'razorpay_payment_id'),
            'classes': ('collapse',)
        }),
        ('Shiprocket Details', {
            'fields': ('shiprocket_order_id', 'shiprocket_shipment_id', 'awb_code', 'courier_name'),
            'classes': ('collapse',)
        }),
        ('Order Status', {
            'fields': ('status', 'created_at', 'packed_at', 'shipped_at', 'delivered_at', 
                      'canceled_at', 'return_requested_at', 'return_approved_at', 
                      'returned_at', 'refunded_at')
        }),
        ('Products', {
            'fields': ('products',),
            'classes': ('collapse',)
        }),
    )
    
    def get_status_display(self, obj):
        return obj.get_status_display()
    get_status_display.short_description = 'Status'
    
    def get_payment_status_display(self, obj):
        return obj.get_payment_status_display()
    get_payment_status_display.short_description = 'Payment Status'
    
    def save_model(self, request, obj, form, change):
        # Only update timestamps if status is changing
        if change:
            try:
                original = Order.objects.get(pk=obj.pk)
                
                # Check if status changed
                if original.status != obj.status:
                    # Automatically set timestamp based on new status
                    now = timezone.now()
                    
                    if obj.status == Order.PACKED and not obj.packed_at:
                        obj.packed_at = now
                    elif obj.status == Order.SHIPPED and not obj.shipped_at:
                        obj.shipped_at = now
                    elif obj.status == Order.OUT_FOR_DELIVERY and not obj.out_for_delivery_at:
                        obj.out_for_delivery_at = now
                    elif obj.status == Order.DELIVERED and not obj.delivered_at:
                        obj.delivered_at = now
                    elif obj.status == Order.CANCELED and not obj.canceled_at:
                        obj.canceled_at = now
                    elif obj.status == Order.RETURN_REQUESTED and not obj.return_requested_at:
                        obj.return_requested_at = now
                    elif obj.status == Order.RETURN_APPROVED and not obj.return_approved_at:
                        obj.return_approved_at = now
                    elif obj.status == Order.RETURNED and not obj.returned_at:
                        obj.returned_at = now
                    elif obj.status == Order.REFUNDED and not obj.refunded_at:
                        obj.refunded_at = now
                        
            except Order.DoesNotExist:
                pass  # New order, no original
        
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        # Show all orders for superusers, only user's orders for others
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

# Register all models
admin.site.register(carousel)
admin.site.register(category)
admin.site.register(product)
admin.site.register(Cart)
admin.site.register(favourite)
admin.site.register(addressModel)
admin.site.register(OrderItem)
admin.site.register(OTPVerification)
admin.site.register(SupportIssue)
admin.site.register(Order, OrderAdmin)  # Register Order with custom admin