import threading
import io
from django.shortcuts import render,redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.http import JsonResponse
from .forms import customuserform,addressForm,supportForm
from .models import *
from django.contrib import messages
from django.contrib.auth import login,authenticate,logout
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404,redirect
from django.utils import timezone
from django.conf import settings
import razorpay
from django.core.mail import send_mail
import random
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import uuid
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
client.set_app_details({"title": "Shop", "version": "1.0"})

@login_required 
def checkout_view(request):
    cart_count=Cart.objects.filter(user=request.user.id).count()
    wish_count=favourite.objects.filter(user=request.user.id).count()
    order_count=Order.objects.filter(user=request.user.id).count()
    user = request.user
    cart_items = Cart.objects.filter(user=user)
    total_cost = sum(item.total_cost for item in cart_items)
    
    if not cart_items.exists():
      
        return redirect('cart')
    
    for item in cart_items:
        item.total = item.product_qty * item.Product.selling_price
        
    if request.method == 'POST':
        form = addressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            
            payment_mode = request.POST.get('payment_mode')
            order_id = (uuid.uuid4()).hex[:10]
            final_order_id = F"Order-{order_id}"
            
            if payment_mode == "COD":
              order = Order.objects.create(
                user=user,
                address=address,
                payment_method='COD',
                total_cost = total_cost,
                final_order_id=final_order_id,
                products=cart_items.first().Product,
                
              )
              order_items=[]
              for item in cart_items:
                
                  order_item =OrderItem.objects.create(
                    order=order,
                    Product=item.Product,
                    quantity=item.product_qty,
                    price=item.Product.selling_price
                  )
                  order_items.append(order_item)
              cart_items.delete()
            
              order_items = OrderItem.objects.filter(order=order)
              sent_order_confirmation_mail(user, order,order_items,final_order_id, request)
              
              context = {
                    'message': 'Order placed successfully with COD.',
                    'final_order_id': final_order_id,
                    'payment_method': 'COD',
                    'cart_count': cart_count,
                    'wish_count': wish_count,
                    'order_count': order_count,
                }
            
           
              return render(request, 'Shop/success.html')
            
            
            elif payment_mode == "Razorpay":
                 
                amount_in_paise = int(total_cost * 100)
                
                razorpay_order = client.order.create({
                'amount': amount_in_paise, 
                'currency': 'INR',
                'payment_capture': '1'
            })
            order = Order.objects.create(
                user=user,
                address=address,
                payment_method='Razorpay',
                total_cost = total_cost,
                razorpay_order_id=razorpay_order['id'],
                products=cart_items.first().Product,
            )
            order_items=[]
            for item in cart_items:
                
                 order_item =OrderItem.objects.create(
                    order=order,
                    Product=item.Product,
                    quantity=item.product_qty,
                    price=item.Product.selling_price
                    
                )
                 order_items.append(order_item)
            cart_items.delete()

           
            
            order_items = OrderItem.objects.filter(order=order)
            sent_order_confirmation_mail(user, order,order_items, razorpay_order['id'], request)
            
            context = {
                'form': form,
                'cart_items': cart_items,
                'total_cost': total_cost,
                'final_order_id':final_order_id,
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key': settings.RAZORPAY_KEY_ID,
                'amount': amount_in_paise,
                 'payment_method': 'Razorpay',
                'currency': 'INR',
                "cart_count":cart_count,
                "wish_count":wish_count,
                "order_count":order_count,
            }
            return render(request, 'Shop/success.html', context)
    else:
        form = addressForm()

    context = {
        'form': form,
        'cart_items': cart_items,
        'total_cost': total_cost,
        "cart_count":cart_count,
        "wish_count":wish_count,
        "order_count":order_count,
        
    }
    return render(request, 'Shop/checkout.html', context)



def sent_order_confirmation_mail(user, order,order_items, razorpay_order_id, request):
    subject = "Order Confirmation"

    html_message = render_to_string('Shop/order_mail.html',{
        'user':user,
        'order':order,
        'order_items':order_items,
        'razorpay_order_id':razorpay_order_id
        
        })
    plain_message = strip_tags(html_message)
    from_mail = 'trumpkartshoppy@gmail.com'
    to = user.email
    
    send_mail(subject,plain_message,from_mail,[to],html_message = html_message)
    
@login_required
def order_view(request):
    cart_count=Cart.objects.filter(user=request.user.id).count()
    wish_count=favourite.objects.filter(user=request.user.id).count()
    order_count=Order.objects.filter(user=request.user.id).count()
    user=request.user
    orders= Order.objects.filter(user=user).order_by('id')
    context={
        "cart_count":cart_count,
        "wish_count":wish_count,
        "order_count":order_count,
        "orders":orders
    }
    return render(request, 'Shop/orders.html', context)


def invoice_view(request,order_id):
    order =get_object_or_404(Order,id=order_id, user=request.user)
    context={
        'order': order
    }
    return render(request,'Shop/invoice.html',context)

def pdf_view(request,order_id):
    order = get_object_or_404(Order, id=order_id)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    elements = []

    pdfmetrics.registerFont(TTFont('Vera', 'Vera.ttf'))
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Rupees', fontName='Vera', fontSize=12))
    
    elements.append(Paragraph("<b>TrumpKart</b>", styles['Title']))
    
    elements.append(Paragraph("<b>Invoice</b>", styles['Heading2']))
    
    elements.append(Paragraph(f"Order ID: {order.id}", styles['Normal']))
    elements.append(Paragraph(f"Date: {order.created_at.strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Paragraph(f"Total Amount: {order.total_cost}", styles['Rupees']))
    
    elements.append(Spacer(1, 12))

    for item in order.order_items.all():
        elements.append(Paragraph(f"Product: {item.Product.name}", styles['Normal']))
        elements.append(Paragraph(f"Sold By: {item.Product.vendor}", styles['Normal']))
        elements.append(Paragraph(f"Price: {item.price}", styles['Rupees']))
        elements.append(Paragraph(f"Quantity: {item.quantity}", styles['Normal']))
        elements.append(Spacer(1, 12))  
    
    address = order.address 
    elements.append(Spacer(1, 24))
    elements.append(Paragraph("Shipping Address:", styles['Heading3']))
    elements.append(Paragraph(f"{address.name}", styles['Normal']))
    elements.append(Paragraph(f"{address.house}, {address.area}", styles['Normal']))
    elements.append(Paragraph(f"{address.city}, {address.state}", styles['Normal']))
    elements.append(Paragraph(f"{address.country}, {address.zipcode}", styles['Normal']))
    elements.append(Paragraph(f"{address.phone}", styles['Normal']))
    elements.append(Paragraph(f"{address.email}", styles['Normal']))
    
    
    note = """
    <b>Note:</b> Thank you for your purchase! If you have any questions about your order or need assistance,
    please contact our customer support team. We appreciate your business and hope to serve you again in the future.
    """
    elements.append(Spacer(1, 48))  
    elements.append(Paragraph(note, styles['Normal']))


    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response

@login_required
def order_delivered_view(request,order_id):
    order=get_object_or_404(Order, id=order_id, user=request.user)
    mark_order_delivered(order)
    return redirect('order_view')

def mark_order_delivered(order):
    order.status = False
    order.delivered_at= timezone.now()
    order.save()
    
def cancel_order_view(request,order_id):
    order=get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == "POST":
        order.status= Order.CANCELED
        order.save()
        return redirect('order')

def return_order_view(request,order_id):
    order=get_object_or_404(Order, id=order_id, user=request.user)
    if request.method =="POST":
        order.status= Order.RETURN
        order.save()
        return redirect('order')    

def homepage(request):
    slides=carousel.objects.all()
    categorys=category.objects.all()
    products=product.objects.filter(trending=1)
    cart_count=Cart.objects.filter(user=request.user.id).count()
    wish_count=favourite.objects.filter(user=request.user.id).count()
    order_count=Order.objects.filter(user=request.user.id).count()
    
    
    context={
        "slides":slides,
        "categorys":categorys,
        "products":products,
        "cart_count":cart_count,
        "wish_count":wish_count,
        "order_count":order_count,  
        "title":"Hot Deals",
        "Hot": "Hot",
        "off":"off",
        "category_title":"CATEGORY"
        
    }
    return render(request,'Shop/dashboard/home.html', context)


def add_to_cart(request):
    if request.headers.get('X-requested-with')=='XMLHttpRequest':
        if request.user.is_authenticated:
            data=json.load(request)
            product_qty=data['product_qty']
            Product_id=data['pid']
            print(request.user.id)
            product_status=product.objects.get(id=Product_id)
               
            if product_status:
                if Cart.objects.filter(user=request.user.id,Product_id=Product_id):
                   return JsonResponse({'status':'product already in cart'} ,status=200)
                else:
                    if product_status.quantity >=product_qty:
                        Cart.objects.create(user=request.user,Product_id=Product_id,product_qty=product_qty)
                        return JsonResponse({'status':'Products added to cart'}, status =200)
                    else:
                            return JsonResponse({'status':"product Stock Not Available"}, status=200)
        else:
            return JsonResponse({'status':"Login to add to cart"}, status=200)
    else:
        return JsonResponse({'status':'Invalid Access'}, status=200)
    
    return redirect('/cart')

@login_required
def cartpage(request):
    cart_count=Cart.objects.filter(user=request.user.id).count()
    wish_count=favourite.objects.filter(user=request.user.id).count()
    order_count=Order.objects.filter(user=request.user.id).count()
    if request.user.is_authenticated:
        cart=Cart.objects.filter(user=request.user)
        context={
            "cart_count":cart_count,
            "wish_count":wish_count,
            "order_count":order_count,
            "cart":cart
        }
        return render(request,'Shop/cart.html', context)
    else:
        return redirect("/")
    

def removecartpage(request, cid):
    cartitem=Cart.objects.get(id=cid)
    cartitem.delete()
    return redirect('/cart')  

@login_required
def favpage(request):
    if request.method == 'POST':
        try:
            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if request.user.is_authenticated:
                    # Fixed: json.loads() not json.load()
                    data = json.loads(request.body)
                    Product_id = data.get('pid')
                    
                    if not Product_id:
                        return JsonResponse({
                            'status': 'Product ID is required'
                        }, status=400)
                    
                    # Check if product exists
                    try:
                        product_status = product.objects.get(id=Product_id)
                    except product.DoesNotExist:
                        return JsonResponse({
                            'status': 'Product not found'
                        }, status=404)
                    
                    # Check if already in favourites
                    if favourite.objects.filter(user=request.user, Product_id=Product_id).exists():
                        return JsonResponse({
                            'status': 'Product already in wishlist'
                        }, status=200)
                    else:
                        # Add to favourites
                        favourite.objects.create(user=request.user, Product_id=Product_id)
                        # Fixed: Return JsonResponse, not messages.success
                        return JsonResponse({
                            'status': 'Product added to wishlist successfully'
                        }, status=200)
                else:
                    return JsonResponse({
                        'status': 'Login to add to favourites'
                    }, status=401)
            else:
                return JsonResponse({
                    'status': 'Invalid Access'
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            print(f"Error in favpage: {str(e)}")
            return JsonResponse({
                'status': f'Error: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'status': 'Invalid request method'
    }, status=405)


def favview(request):
    cart_count = Cart.objects.filter(user=request.user.id).count()
    wish_count = favourite.objects.filter(user=request.user.id).count()
    order_count = Order.objects.filter(user=request.user.id).count()
    
    if request.user.is_authenticated:
        fav = favourite.objects.filter(user=request.user)
        
        context = {
            "cart_count": cart_count,
            "wish_count": wish_count,
            "order_count": order_count,
            "fav": fav
        }
        return render(request, 'Shop/favourite.html', context)
    else:
        return redirect("/")
   
def removefavrt(request,fid):
    favrtitem=favourite.objects.get(id=fid)
    favrtitem.delete()
    return redirect('/favrt')   

def logout_page(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request,'Logged out Successfully')
    return redirect('/')
    

def login_page(request):
    if request.user.is_authenticated:
        return redirect('/')
    else:
     if request.method == "POST":
        name=request.POST.get('username')
        pwd=request.POST.get('password')
        user=authenticate(request,username=name,password=pwd)
        if user is not None:
            login(request,user)
            messages.success(request,"SuccessFully Logged in")
            return redirect('/')  
        else:
            messages.error(request,"Invalid User name Or Password")
            return redirect('account_login')
        
     return render(request,'Shop/account/login.html')
 
def sent_otp(email, otp):
    subject = 'Your OTP for Registration'
    message = f'Your OTP for Registration is {otp}'
    # FIX: Use DEFAULT_FROM_EMAIL instead of EMAIL_HOST_USER
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    
    try:
        send_mail(subject, message, email_from, recipient_list)
        return True
    except Exception as e:
        # Log the error for debugging
        print(f"Error sending email: {e}")
        return False

def registerpage(request):
    if request.method == 'POST':
        form = customuserform(request.POST)

        email = request.POST.get('email')
        if User.objects.filter(email=email).exists():
            messages.error(request, 'This email is already registered. Please use a different email or login.')
            return render(request, 'shop/account/signup.html', {'form': form})

        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            otp = random.randint(100000, 999999)
            OTPVerification.objects.create(user=user, otp=otp)
            
            # Send OTP and handle errors
            email_sent = sent_otp(user.email, otp)
            
            if not email_sent:
                messages.warning(request, 'Registration successful but email could not be sent. Please contact support.')
            
            return redirect(reverse('otp_verification') + f'?email={user.email}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = customuserform()
    
    return render(request, 'Shop/account/signup.html', {'form': form})


def otp_verification(request):
    email = request.GET.get('email')
    if request.method == 'POST':
        otp = request.POST.get('otp')
        try:
            user_otp = OTPVerification.objects.get(user__email=email, otp=otp)
            user = user_otp.user
            user.is_active = True
            user.save()
            user_otp.delete()  # OTP is used, so delete it
            messages.success(request, "Registration successfull")
            return redirect('account_login')
        except OTPVerification.DoesNotExist:
            return HttpResponse('Invalid OTP. Please try again.')
    return render(request, 'Shop/otp_verification.html', {'email': email})

def collectionpage(request):
    categorys=category.objects.filter(status=0)
    cart_count=Cart.objects.filter(user=request.user.id).count()
    wish_count=favourite.objects.filter(user=request.user.id).count()
    order_count=Order.objects.filter(user=request.user.id).count()
    context={
        "categorys":categorys,
        "cart_count":cart_count,
        "wish_count":wish_count,
        "order_count":order_count,
    }
    return render(request,'Shop/collection.html',context)

def collections(request, name):
    category_obj = category.objects.get(name=name, status=0)
    cart_count=Cart.objects.filter(user=request.user.id).count()
    wish_count=favourite.objects.filter(user=request.user.id).count()
    order_count=Order.objects.filter(user=request.user.id).count()
    
    if category_obj is not None:
        products = product.objects.filter(category=category_obj)
        return render(request, 'Shop/products/index.html',{"products": products, "category_name": name, "category_description": category_obj.description,"category_image":category_obj.image,"cart_count":cart_count,
        "wish_count":wish_count,
        "order_count":order_count,})
    else:
        messages.warning(request, "No such category found")
        return redirect('collection')

def productsDetail(request, cname, pname):
    cart_count = Cart.objects.filter(user=request.user.id).count()
    wish_count = favourite.objects.filter(user=request.user.id).count()
    order_count = Order.objects.filter(user=request.user.id).count()
    
    hot_product = product.objects.filter(trending=1)
    
    if(category.objects.filter(name=cname, status=0)):
        if(product.objects.filter(name=pname, status=0)):
            products = product.objects.filter(name=pname, status=0).first()
            return render(request, 'Shop/products/products_detail.html', {
                "products": products, 
                "hot_product": hot_product,
                "cart_count": cart_count,
                "wish_count": wish_count,
                "order_count": order_count
            })
        else:
            messages.warning(request, "No Such Product Found")
            return redirect('collectionpage') 
    else:
        messages.warning(request, "No Such Category Found")
        return redirect('collectionpage')
            
   
def searchview(request):
    cart_count=Cart.objects.filter(user=request.user.id).count()
    wish_count=favourite.objects.filter(user=request.user.id).count()
    order_count=Order.objects.filter(user=request.user.id).count()
    
    query=request.GET.get('q')
    categories=[]
    products=[]
    
    if query:
        categories=category.objects.filter(name__icontains=query)
        products=product.objects.filter(name__icontains=query)
        
    context={
        'categories':categories,
        'products':products,
        "cart_count":cart_count,
        "wish_count":wish_count,
        "order_count":order_count
    }
    
    return render(request,'Shop/search.html', context)


def aboutview(request):
    
    return render(request,'Shop/about.html')


def privacyview(request):
    return render(request,'Shop/privacy.html')


def faqview (request):
    return render(request, 'Shop/FAQ.html')
 
 
def supportView(request):
    
    section =request.GET.get('section','feedback')
    content={
        'feedback':{
            'heading':'Feedback',
            'paragraph':'We value your feedback! Please share your thoughts with us to help improve your experience.Your opinion matters to us. Let us know how we can make your experience better by providing your feedback.'
        },
        'payments': {
            'heading': 'Payments & Refund',
            'paragraph': 'Learn more about our payments and refund policies to ensure a smooth transaction. We strive to provide transparent and efficient service. Please provide the Order Id and Mobile number for payments and refund relatd problems, Feel free to ask any Question related payment and refund.'
        },
        'shipping': {
            'heading': 'Shipping & Cancellation',
            'paragraph': 'Get details on ofur shipping process and cancellation policies. We aim to make your shopping experience seamless and worry-free. Please the Order_id and and other details if you want to cancel the order or to know the shipping related information. '
        },
        'return': {
            'heading': 'Return',
            'paragraph': 'Understand our return policies to ensure hassle-free returns. Your satisfaction is our priority, and we are here to assist with any concerns. Please provide the Order id that want to return and feel free to ask the Question Related Return Policy.  '
        }
        
    }
    selected_content= content.get(section,content['feedback'])
    if request.method == 'POST':
        form = supportForm(request.POST)
        if form.is_valid():
            name= form.cleaned_data['name']
            email =form.cleaned_data['email']
            feedback = form.cleaned_data['feedback']
            
            SupportIssue.objects.create(
                name=name,
                email=email,
                feedback=feedback
            )
            
            
            send_mail(
                f"mail from {name}",
                feedback,
                email,
                ['trumpkartshoppy@gmail.com'],
                fail_silently=False,
            )
            form= supportForm()
            return JsonResponse({'status':'success', 'message':'Your issue has been Sent Successfully'})
        else:
            return JsonResponse({'status':'error', 'message':'Error in Reporting the Issue Please try again'})
    else:
        form =supportForm()
    return render(request,'Shop/mail.html', {'form': form, 'selected_content': selected_content})