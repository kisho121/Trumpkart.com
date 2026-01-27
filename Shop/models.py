from django.db import models
from django.contrib.auth.models import User 
import datetime
import os 
from django.utils import timezone
import uuid
from cloudinary.models import CloudinaryField
from django.core.validators import MinValueValidator, MaxValueValidator

def getFileName(request,filename):
    now_time=datetime.datetime.now().strftime("%y%m%d%H:%M:%S")
    new_filename="%s%s"%(now_time,filename)
    return os.path.join('uploads/',new_filename)

class OTPVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    
    class Meta:
        db_table = 'shop_otpverification'
    
class carousel(models.Model):
    carousel_image = CloudinaryField('image')
    alt_text = models.CharField(max_length=150, null=False, blank=False, default="slide_image")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'shop_carousel'

class category(models.Model):
    name = models.CharField(max_length=150, null=False, blank=False)
    image = CloudinaryField('image', null=True, blank=True)
    description = models.TextField(max_length=500, null=False, blank=False)
    status = models.BooleanField(default=False, help_text="0-show,1-Hidden")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'shop_category'
    
    def __str__(self):
        return f"{self.name},{self.description}"
    
class product(models.Model):
    category = models.ForeignKey(category, on_delete=models.CASCADE)
    name = models.CharField(max_length=150, null=False, blank=False)
    vendor = models.CharField(max_length=150, null=False, blank=False)
    product_image = CloudinaryField('image', null=True, blank=True)
    product_image_2 = CloudinaryField('image', null=True, blank=True)
    product_image_3 = CloudinaryField('image', null=True, blank=True)
    quantity = models.IntegerField(null=False, blank=False)
    original_price = models.IntegerField(null=False, blank=False)
    selling_price = models.IntegerField(null=False, blank=False)
    description = models.TextField(max_length=1500, null=False, blank=False)
    status = models.BooleanField(default=False, help_text="0-show,1-Hidden")
    created_at = models.DateTimeField(auto_now_add=True)
    trending = models.BooleanField(default=False, help_text="0-default,1-Trending")
    
    class Meta:
        db_table = 'shop_product'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['vendor']),
            models.Index(fields=['category']),
        ]
       
    def __str__(self):
        return self.name
    
    @property
    def discount(self):
        return round(((self.original_price - self.selling_price) / self.original_price) * 100)
    
    @property
    def average_rating(self):
        ratings = self.ratings.all()
        if ratings.exists():
            return round(sum(r.rating for r in ratings) / ratings.count(), 1)
        return 0

    @property
    def rating_count(self):
        return self.ratings.count()

    @property
    def rating_distribution(self):
        """Returns count of each star rating (5 to 1)"""
        distribution = {}
        for star in range(5, 0, -1):
            distribution[star] = self.ratings.filter(rating=star).count()
        return distribution
    
class ProductRating(models.Model):
    product = models.ForeignKey(product, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    review = models.TextField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_rating'
        unique_together = ('product', 'user')  # One rating per user per product
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['product', 'rating']),
            models.Index(fields=['user', 'product']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.rating} stars"


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    Product = models.ForeignKey(product, on_delete=models.CASCADE)
    product_qty = models.IntegerField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'shop_cart'
     
    @property
    def total_cost(self):
        return self.product_qty * self.Product.selling_price
    
class favourite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    Product = models.ForeignKey(product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'shop_favourite'
        
class addressModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True) 
    name = models.CharField(max_length=150)
    house = models.CharField(max_length=150)
    area = models.CharField(max_length=150)
    address = models.TextField(max_length=1500)
    city = models.CharField(max_length=150)
    state = models.CharField(max_length=150)
    country = models.CharField(max_length=150)
    zipcode = models.CharField(max_length=10)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    
    class Meta:
        db_table = 'shop_addressmodel'
    
class Order(models.Model):
    # ==================== ORDER STATUS ====================
    # Normal Flow: 0 → 2 → 3 → 4 → 5
    PLACED = 0              # Order placed, payment pending/confirmed
    PACKED = 1              # Order packed by dealer/admin
    SHIPPED = 2             # Handed over to courier/delivery
    OUT_FOR_DELIVERY = 3    # Out for delivery by delivery person
    DELIVERED = 4           # Successfully delivered to customer
    
    # Cancellation (Can happen before SHIPPED)
    CANCELED = 5            # Order canceled by customer/admin
    
    # Return Flow (After DELIVERED): 4 → 6 → 7 → 8
    RETURN_REQUESTED = 6    # Customer requested return
    RETURN_APPROVED = 7     # Return approved, product picked up
    RETURNED = 8            # Product returned to warehouse
    REFUNDED = 9            # Money refunded to customer

    STATUS_CHOICES = [
        (PLACED, 'Order Placed'),
        (PACKED, 'Packed'),
        (SHIPPED, 'Shipped'),
        (OUT_FOR_DELIVERY, 'Out for Delivery'),
        (DELIVERED, 'Delivered'),
        (CANCELED, 'Canceled'),
        (RETURN_REQUESTED, 'Return Requested'),
        (RETURN_APPROVED, 'Return Approved'),
        (RETURNED, 'Returned'),
        (REFUNDED, 'Refunded'),
    ]

    # ==================== PAYMENT STATUS ====================
    PAYMENT_PENDING = 'pending'      # COD or payment not completed
    PAYMENT_COMPLETED = 'completed'  # Razorpay payment successful
    PAYMENT_FAILED = 'failed'        # Online payment failed
    PAYMENT_COD_COLLECTED = 'cod_collected'  # COD collected by delivery person
    PAYMENT_REFUNDED = 'refunded'    # Money refunded (for returns)

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, 'Pending'),
        (PAYMENT_COMPLETED, 'Completed'),
        (PAYMENT_FAILED, 'Failed'),
        (PAYMENT_COD_COLLECTED, 'COD Collected'),
        (PAYMENT_REFUNDED, 'Refunded'),
    ]

    # ==================== FIELDS ====================
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address = models.ForeignKey('addressModel', on_delete=models.CASCADE)
    
    # Payment Info
    payment_method = models.CharField(max_length=20)  # 'COD' or 'Razorpay'
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_PENDING
    )
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Order IDs
    final_order_id = models.CharField(max_length=255, null=True, blank=True)  # ORD-XXX
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    cod_order_id = models.UUIDField(default=uuid.uuid4, unique=True)
    
    # Shiprocket Integration (NEW)
    shiprocket_order_id = models.CharField(max_length=100, blank=True, null=True)
    shiprocket_shipment_id = models.CharField(max_length=100, blank=True, null=True)
    awb_code = models.CharField(max_length=100, blank=True, null=True)  # Tracking number
    courier_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Status
    status = models.IntegerField(choices=STATUS_CHOICES, default=PLACED)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    packed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    out_for_delivery_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    return_requested_at = models.DateTimeField(null=True, blank=True)
    return_approved_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    
    # Legacy field (keeping for compatibility)
    products = models.ForeignKey('product', on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'shop_order'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.final_order_id or self.id} by {self.user.username}"
    
    # ==================== PROPERTIES ====================
    
    @property
    def customer_status(self):
        """User-friendly status messages for customers"""
        status_messages = {
            self.PLACED: "Order Placed Successfully",
            self.PACKED: "Your Order is Being Packed",
            self.SHIPPED: "Order Shipped",
            self.OUT_FOR_DELIVERY: "Out for Delivery",
            self.DELIVERED: "Delivered Successfully",
            self.CANCELED: "Order Canceled",
            self.RETURN_REQUESTED: "Return Request Submitted",
            self.RETURN_APPROVED: "Return Approved - Pickup Scheduled",
            self.RETURNED: "Product Returned",
            self.REFUNDED: "Refund Processed",
        }
        return status_messages.get(self.status, "Unknown Status")
    
    @property
    def can_cancel(self):
        """Check if order can be canceled"""
        return self.status in [self.PLACED, self.PACKED]
    
    @property
    def can_return(self):
        """Check if order can be returned (within 10 days of delivery)"""
        if self.status == self.DELIVERED and self.delivered_at:
            days_since_delivery = (timezone.now() - self.delivered_at).days
            return days_since_delivery <= 10
        return False
    
    @property
    def is_cod(self):
        """Check if this is a COD order"""
        return self.payment_method.upper() == 'COD'
    
    @property
    def is_returnable(self):
        """Alias for can_return"""
        return self.can_return
    
    @property
    def tracking_available(self):
        """Check if tracking information is available"""
        return bool(self.awb_code)
    
    @property
    def payment_collected(self):
        """Check if payment has been collected/completed"""
        return self.payment_status in [
            self.PAYMENT_COMPLETED, 
            self.PAYMENT_COD_COLLECTED
        ]
    
    # ==================== METHODS ====================
    
    def mark_as_packed(self):
        """Mark order as packed"""
        self.status = self.PACKED
        self.packed_at = timezone.now()
        self.save()
    
    def mark_as_shipped(self, shiprocket_data=None):
        """Mark order as shipped"""
        self.status = self.SHIPPED
        self.shipped_at = timezone.now()
        
        if shiprocket_data:
            self.shiprocket_order_id = shiprocket_data.get('order_id')
            self.shiprocket_shipment_id = shiprocket_data.get('shipment_id')
            self.awb_code = shiprocket_data.get('awb_code')
            self.courier_name = shiprocket_data.get('courier_name')
        
        self.save()
    
    def mark_as_out_for_delivery(self):
        """Mark order as out for delivery"""
        self.status = self.OUT_FOR_DELIVERY
        self.out_for_delivery_at = timezone.now()
        self.save()
    
    def mark_as_delivered(self, cod_collected=False):
        """Mark order as delivered"""
        self.status = self.DELIVERED
        self.delivered_at = timezone.now()
        
        # Update payment status for COD
        if self.is_cod and cod_collected:
            self.payment_status = self.PAYMENT_COD_COLLECTED
        
        self.save()
    
    def cancel_order(self, reason=None):
        """Cancel the order"""
        if not self.can_cancel:
            raise ValueError("Order cannot be canceled at this stage")
        
        self.status = self.CANCELED
        self.canceled_at = timezone.now()
        self.save()
    
    def request_return(self):
        """Request return"""
        if not self.can_return:
            raise ValueError("Order cannot be returned")
        
        self.status = self.RETURN_REQUESTED
        self.return_requested_at = timezone.now()
        self.save()
    
    def approve_return(self):
        """Approve return request"""
        if self.status != self.RETURN_REQUESTED:
            raise ValueError("No return request found")
        
        self.status = self.RETURN_APPROVED
        self.return_approved_at = timezone.now() 
        self.save()
    
    def mark_as_returned(self):
        """Mark product as returned"""
        self.status = self.RETURNED
        self.returned_at = timezone.now()
        self.save()
    
    def process_refund(self):
        """Process refund"""
        self.status = self.REFUNDED
        self.refunded_at = timezone.now()
        self.payment_status = self.PAYMENT_REFUNDED
        self.save()   
        
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    Product = models.ForeignKey(product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2) 
    class Meta:
        db_table = 'shop_orderitem'

    def __str__(self):
        return f"OrderItem: {self.quantity} of {self.Product.name}" 
    
class SupportIssue(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    feedback = models.TextField()
    
    class Meta:
        db_table = 'shop_supportissue'

    def __str__(self):
        return self.name