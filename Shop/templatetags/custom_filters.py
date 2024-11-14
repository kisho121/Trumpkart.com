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