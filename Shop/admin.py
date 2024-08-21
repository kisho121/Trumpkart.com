from django.contrib import admin
from .models import*
from .models import category, product, Cart, Order, OrderItem, favourite, addressModel
"""
class categoryDetail(admin.ModelAdmin):
    list_display=('name','image', 'description')
    """
admin.site.register(carousel)
admin.site.register(category)
admin.site.register(product)
admin.site.register(Cart)
admin.site.register(favourite)
admin.site.register(addressModel)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(OTPVerification)
admin.site.register(SupportIssue)

