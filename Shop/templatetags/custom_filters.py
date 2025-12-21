# your_app/templatetags/your_custom_filters.py
from django import template

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