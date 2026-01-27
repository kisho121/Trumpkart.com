# your_app/templatetags/your_custom_filters.py
from django import template
from django.utils import timezone
from datetime import date, timedelta

register = template.Library()

# Custom filter to check if the length of a list or string is equal to a specified value
@register.filter
def is_length(value, arg):
    try:
        return len(value) == int(arg)  # Returns True if length matches
    except (TypeError, ValueError):
        return False  # Returns False if value isn't iterable or arg isn't a valid integer
    
# Custom filter to multiply two values
@register.filter
def mul(value, arg):
    """Multiply the value by the arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
    
# REMOVE THIS DUPLICATE:
# @register.filter
# def mul(value, arg):
#     try:
#         return float(value) * float(arg)
#     except (ValueError, TypeError):
#         return 0

@register.filter
def div(value, arg):
    try:
        return float(value) / float(arg) if arg != 0 else 0
    except (ValueError, TypeError):
        return 0
    
@register.filter
def format_with_pipe(value):
    """Format date as 'Jan 22, 2025 | 14:30' with pipe symbol"""
    if not value:
        return ""
    
    # Convert to local timezone if it's timezone-aware
    if timezone.is_aware(value):
        local_time = timezone.localtime(value)
    else:
        local_time = value
    
    # Format with pipe symbol
    return local_time.strftime("%b %d, %Y | %H:%M")

@register.filter
def can_cancel_order(order):
    """Check if order can be canceled (PLACED or PACKED status)"""
    return order.status in [order.PLACED, order.PACKED]

@register.filter
def can_return_order(order):
    """Check if order can be returned (within 10 days of delivery)"""
    if order.status != order.DELIVERED:
        return False
    
    if not order.delivered_at:
        return False
    
    # Check if within 10 days
    cutoff_date = order.delivered_at + timedelta(days=10)
    return timezone.now() <= cutoff_date

@register.filter
def return_days_left(order):
    """Calculate days left for return"""
    if not order.delivered_at or order.status != order.DELIVERED:
        return 0
    
    cutoff_date = order.delivered_at + timedelta(days=10)
    days_left = (cutoff_date - timezone.now()).days
    return max(0, days_left)

@register.filter
def get_order_status_text(order):
    """Get user-friendly status text"""
    status_map = {
        order.PLACED: "Order Placed",
        order.PACKED: "Packed",
        order.SHIPPED: "Shipped",
        order.OUT_FOR_DELIVERY: "Out for Delivery",
        order.DELIVERED: "Delivered",
        order.CANCELED: "Canceled",
        order.RETURN_REQUESTED: "Return Requested",
        order.RETURN_APPROVED: "Return Approved",
        order.RETURNED: "Returned",
        order.REFUNDED: "Refunded",
    }
    return status_map.get(order.status, "Unknown")

@register.filter
def get_order_status_class(order):
    """Get Bootstrap class for status badge"""
    status_class_map = {
        order.PLACED: "info",
        order.PACKED: "primary",
        order.SHIPPED: "primary",
        order.OUT_FOR_DELIVERY: "warning",
        order.DELIVERED: "success",
        order.CANCELED: "danger",
        order.RETURN_REQUESTED: "warning",
        order.RETURN_APPROVED: "info",
        order.RETURNED: "secondary",
        order.REFUNDED: "success",
    }
    return status_class_map.get(order.status, "secondary")