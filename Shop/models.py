from django.db import models
from django.contrib.auth.models import User 
import datetime
import os 
from django.utils import timezone
import uuid

def getFileName(request,filename):
    now_time=datetime.datetime.now().strftime("%y%m%d%H:%M:%S")
    new_filename="%s%s"%(now_time,filename)
    return os.path.join('uploads/',new_filename)

class OTPVerification(models.Model):
    user =models.OneToOneField(User, on_delete=models.CASCADE)
    otp =models.CharField(max_length=6)
    
class carousel(models.Model):
    carousel_image= models.ImageField(upload_to=getFileName)
    alt_text=models.CharField(max_length=150, null=False,blank=False,default="slide_image")
    created_at=models.DateTimeField(auto_now_add=True)

class category(models.Model):
    name=models.CharField(max_length=150,null=False,blank=False)
    image=models.ImageField(upload_to=getFileName,null=True,blank=True)
    description=models.TextField(max_length=500,null=False,blank=False)
    status=models.BooleanField(default=False,help_text="0-show,1-Hidden")
    created_at=models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name},{self.description}"
    
class product(models.Model):
    category=models.ForeignKey(category,on_delete=models.CASCADE)
    name=models.CharField(max_length=150,null=False,blank=False)
    vendor=models.CharField(max_length=150,null=False,blank=False)
    product_image=models.ImageField(upload_to=getFileName,null=True,blank=True)
    quantity=models.IntegerField(null=False,blank=False)
    original_price=models.IntegerField(null=False,blank=False)
    selling_price=models.IntegerField(null=False,blank=False)
    description=models.TextField(max_length=1500,null=False,blank=False)
    status=models.BooleanField(default=False,help_text="0-show,1-Hidden")
    created_at=models.DateTimeField(auto_now_add=True)
    trending=models.BooleanField(default=False,help_text="0-default,1-Trending")
       
    def __str__(self):
        return self.name
    
    @property
    def discount(self):
        return round(((self.original_price - self.selling_price) / self.original_price) * 100)

class Cart(models.Model):
    user =models.ForeignKey(User,on_delete=models.CASCADE)
    Product = models.ForeignKey(product, on_delete=models.CASCADE)
    product_qty = models.IntegerField(null=False,blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
     
    @property
    def total_cost(self):
        return self.product_qty*self.Product.selling_price
    
class favourite(models.Model):
    user =models.ForeignKey(User,on_delete=models.CASCADE)
    Product = models.ForeignKey(product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
        
class addressModel(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,null=True,blank=True) 
    name=models.CharField(max_length=150)
    house=models.CharField(max_length=150)
    area =models.CharField(max_length=150)
    address=models.TextField(max_length=1500)
    city=models.CharField(max_length=150)
    state=models.CharField(max_length=150)
    country=models.CharField(max_length=150)
    zipcode = models.CharField(max_length=10)
    phone=models.CharField( max_length=20)
    email=models.EmailField()
    
    
    
class Order(models.Model):
    PENDING = 0
    DELIVERED = 1
    CANCELED =2
    RETURN = 3

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (DELIVERED, 'Delivered'),
        (CANCELED, 'Canceled'),
        (RETURN, 'Return'),
    ]
   
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address = models.ForeignKey(addressModel, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=20)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    final_order_id = models.CharField(max_length=255, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at =models.DateTimeField(null=True, blank=True)
    status= models.IntegerField(choices=STATUS_CHOICES, default=PENDING)
    products = models.ForeignKey(product, on_delete=models.CASCADE)
    cod_order_id = models.UUIDField(default=uuid.uuid4, unique=True)



    
    def __str__(self):
        return f"Order {self.id} by {self.user.username}"
    
    @property
    def is_old_order(self):
        if self.delivered_at:
            return timezone.now() - self.delivered_at > timezone.timedelta(days = 10)
        return False
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order,related_name='order_items', on_delete=models.CASCADE)
    Product = models.ForeignKey(product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"OrderItem: {self.quantity} of {self.Product.name}" 
    
from django.db import models

class SupportIssue(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    feedback = models.TextField()

    def __str__(self):
        return self.name
