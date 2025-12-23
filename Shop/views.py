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
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from django.db.models import Q
import re
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime


client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
client.set_app_details({"title": "Shop", "version": "1.0"})

@login_required 
def checkout_view(request):
    user = request.user
    cart_items = Cart.objects.filter(user=user)
    
    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty')
        return redirect('cart')
    
    # Calculate totals
    total_cost = sum(item.product_qty * item.Product.selling_price for item in cart_items)
    
    # Add total to each item for display
    for item in cart_items:
        item.total = item.product_qty * item.Product.selling_price
    
    # Get counts for navbar
    cart_count = cart_items.count()
    wish_count = favourite.objects.filter(user=user).count()
    order_count = Order.objects.filter(user=user).count()
    
    if request.method == 'POST':
        # Check if it's an AJAX request for creating Razorpay order
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            payment_mode = request.POST.get('payment_mode')
            
            if payment_mode == 'Razorpay':
                # Validate form
                form = addressForm(request.POST)
                if not form.is_valid():
                    return JsonResponse({
                        'success': False,
                        'message': 'Please fill all required fields correctly.'
                    }, status=400)
                
                try:
                    # Create Razorpay order
                    amount_in_paise = int(total_cost * 100)
                    
                    razorpay_order = client.order.create({
                        'amount': amount_in_paise,
                        'currency': 'INR',
                        'payment_capture': '1'
                    })
                    
                    return JsonResponse({
                        'success': True,
                        'razorpay_order_id': razorpay_order['id'],
                        'amount': amount_in_paise,
                        'currency': 'INR'
                    })
                    
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'message': f'Failed to create payment order: {str(e)}'
                    }, status=500)
        
        # Regular form submission (after payment)
        form = addressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = user
            address.save()
            
            payment_mode = request.POST.get('payment_mode')
            
            if not payment_mode:
                messages.error(request, 'Please select a payment method')
                return redirect('checkout')
            
            # Generate order ID
            order_uuid = uuid.uuid4().hex[:10]
            final_order_id = f"ORD-{order_uuid}"
            
            if payment_mode == "COD":
                # Create order for COD
                order = Order.objects.create(
                    user=user,
                    address=address,
                    payment_method='COD',
                    total_cost=total_cost,
                    final_order_id=final_order_id,
                    products=cart_items.first().Product,
                    payment_status='Pending',
                    status=Order.PENDING
                )
                
                # Create order items
                order_items = []
                for item in cart_items:
                    order_item = OrderItem.objects.create(
                        order=order,
                        Product=item.Product,
                        quantity=item.product_qty,
                        price=item.Product.selling_price
                    )
                    order_items.append(order_item)
                    
                    # Reduce product stock
                    product_obj = item.Product
                    if product_obj.quantity >= item.product_qty:
                        product_obj.quantity -= item.product_qty
                        product_obj.save()
                    else:
                        messages.error(request, f'{product_obj.name} is out of stock')
                        order.delete()
                        return redirect('cart')
                
                # Clear cart
                cart_items.delete()
                
                # Send confirmation email
                try:
                    sent_order_confirmation_mail(user, order, order_items, final_order_id, request)
                except Exception as e:
                    print(f"Email sending failed: {e}")

                cart_count = 0  # Cart is now empty
                wish_count = favourite.objects.filter(user=user).count()
                order_count = Order.objects.filter(user=user).count()
                
                # Redirect to success page with order details
                return render(request, 'Shop/success.html', {
                    'order': order,
                    'order_items': order_items,
                    'final_order_id': final_order_id,
                    'message': 'Order placed successfully with Cash on Delivery!',
                    'payment_method': 'COD',
                    'cart_count': cart_count,
                    'wish_count': wish_count,
                    'order_count': order_count
                })
            
            elif payment_mode == "Razorpay":
                # Verify payment signature
                razorpay_payment_id = request.POST.get('razorpay_payment_id')
                razorpay_order_id = request.POST.get('razorpay_order_id')
                razorpay_signature = request.POST.get('razorpay_signature')
                
                if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
                    messages.error(request, 'Payment verification failed. Missing payment details.')
                    return redirect('checkout')
                
                try:
                    # Verify signature
                    params_dict = {
                        'razorpay_order_id': razorpay_order_id,
                        'razorpay_payment_id': razorpay_payment_id,
                        'razorpay_signature': razorpay_signature
                    }
                    
                    # This will raise an error if verification fails
                    client.utility.verify_payment_signature(params_dict)
                    
                    # Payment verified - create order
                    order = Order.objects.create(
                        user=user,
                        address=address,
                        payment_method='Razorpay',
                        total_cost=total_cost,
                        razorpay_order_id=razorpay_order_id,
                        razorpay_payment_id=razorpay_payment_id,
                        final_order_id=final_order_id,
                        products=cart_items.first().Product,
                        payment_status='Completed',
                        status=Order.PENDING
                    )
                    
                    # Create order items
                    order_items = []
                    for item in cart_items:
                        order_item = OrderItem.objects.create(
                            order=order,
                            Product=item.Product,
                            quantity=item.product_qty,
                            price=item.Product.selling_price
                        )
                        order_items.append(order_item)
                        
                        # Reduce product stock
                        product_obj = item.Product
                        if product_obj.quantity >= item.product_qty:
                            product_obj.quantity -= item.product_qty
                            product_obj.save()
                        else:
                            messages.error(request, f'{product_obj.name} is out of stock')
                            order.delete()
                            return redirect('cart')
                    
                    # Clear cart
                    cart_items.delete()
                    
                    # Send confirmation email
                    try:
                        sent_order_confirmation_mail(user, order, order_items, final_order_id, request)
                    except Exception as e:
                        print(f"Email sending failed: {e}")

                    cart_count = 0  # Cart is now empty
                    wish_count = favourite.objects.filter(user=user).count()
                    order_count = Order.objects.filter(user=user).count()
                        
                    # Redirect to success page with order details
                    return render(request, 'Shop/success.html', {
                        'order': order,
                        'order_items': order_items,
                        'final_order_id': final_order_id,
                        'razorpay_order_id': razorpay_order_id,
                        'razorpay_payment_id': razorpay_payment_id,
                        'message': 'Payment successful! Your order has been placed.',
                        'payment_method': 'Razorpay',
                        'cart_count': cart_count,
                        'wish_count': wish_count,
                        'order_count': order_count
                    })
                    
                except razorpay.errors.SignatureVerificationError:
                    messages.error(request, 'Payment verification failed. Please contact support with your payment ID.')
                    return redirect('checkout')
                except Exception as e:
                    messages.error(request, f'Order creation failed: {str(e)}')
                    return redirect('checkout')
        else:
            # Form has errors
            messages.error(request, 'Please fill all required fields correctly.')
    else:
        form = addressForm()
    
    context = {
        'form': form,
        'cart_items': cart_items,
        'total_cost': total_cost,
        'amount': int(total_cost * 100),  # Amount in paise
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'cart_count': cart_count,
        'wish_count': wish_count,
        'order_count': order_count,
    }
    return render(request, 'Shop/checkout.html', context)


def sent_order_confirmation_mail(user, order, order_items, order_id, request):
    """Send order confirmation email"""
    subject = "Order Confirmation - TrumpKart"
    
    html_message = render_to_string('Shop/order_mail.html', {
        'user': user,
        'order': order,
        'order_items': order_items,
        'order_id': order_id
    })
    plain_message = strip_tags(html_message)
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]
    
    try:
        send_mail(
            subject,
            plain_message,
            from_email,
            recipient_list,
            html_message=html_message,
            fail_silently=False
        )
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def sent_order_confirmation_mail(user, order, order_items, razorpay_order_id, request):
    subject = "Order Confirmation"

    html_message = render_to_string('Shop/order_mail.html', {
        'user': user,
        'order': order,
        'order_items': order_items,
        'razorpay_order_id': razorpay_order_id
    })
    plain_message = strip_tags(html_message)
    
    # Use your verified SendGrid sender email or settings.DEFAULT_FROM_EMAIL
    from_mail = settings.DEFAULT_FROM_EMAIL  # Make sure this is verified in SendGrid
    to = user.email
    
    send_mail(subject, plain_message, from_mail, [to], html_message=html_message)
    
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
    cart_count=Cart.objects.filter(user=request.user.id).count()
    wish_count=favourite.objects.filter(user=request.user.id).count()
    order_count=Order.objects.filter(user=request.user.id).count()
    user=request.user
    orders= Order.objects.filter(user=user).order_by('id')
    
    order =get_object_or_404(Order,id=order_id, user=request.user)
    context={
        'order': order,
        "cart_count":cart_count,
        "wish_count":wish_count,
        "order_count":order_count,
        "orders":orders
    }
    return render(request,'Shop/invoice.html',context)


def pdf_view(request, order_id):
    """Generate professional invoice PDF - Enhanced Full Page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Create HTTP response with PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="TrumpKart_Invoice_{order.final_order_id}.pdf"'
    
    # Create PDF buffer
    buffer = io.BytesIO()
    
    # Create PDF document - larger margins for better spacing
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=40,
        bottomMargin=40
    )
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles with LARGER sizing
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=32,  # Increased from 24
        textColor=colors.HexColor('#667eea'),
        spaceAfter=8,  # Increased spacing
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=13,  # Increased from 10
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=20  # Increased from 12
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,  # Increased from 12
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=10,  # Increased from 6
        spaceBefore=15,  # Increased from 8
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,  # Increased from 10
        textColor=colors.HexColor('#4b5563'),
        spaceAfter=6,  # Increased from 3
        leading=18  # Increased from 14
    )
    
    # Header Section - LARGER
    elements.append(Paragraph("TRUMPKART", title_style))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("Your Trusted Shopping Partner", subtitle_style))
    elements.append(Spacer(1, 0.1 * inch))

    # Invoice title - LARGER
    invoice_title_data = [['TAX INVOICE']]
    invoice_title_table = Table(invoice_title_data, colWidths=[6.8 * inch])
    invoice_title_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 18),  # Increased from 16
        ('TOPPADDING', (0, 0), (-1, -1), 14),  # Increased padding
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
    ]))
    elements.append(invoice_title_table)
    elements.append(Spacer(1, 0.3 * inch))  # Increased spacing
    
    # Determine payment status
    if order.payment_method == 'COD':
        payment_status = 'Paid'
    else:
        payment_status = order.payment_status
    
    # Invoice Details and Company Info - LARGER TEXT
    invoice_info_data = [
        [
            Paragraph(f"<b>Invoice Details</b><br/><br/>"
                     f"<font size=11>Invoice No: <b>{order.final_order_id}</b><br/>"
                     f"Order ID: <b>{order.id}</b><br/>"
                     f"Date: <b>{order.created_at.strftime('%d %B %Y')}</b><br/>"
                     f"Payment: <b>{order.payment_method}</b><br/>"
                     f"Status: <b>{payment_status}</b></font>", 
                     normal_style),
            
            Paragraph("<b>TrumpKart Store</b><br/><br/>"
                     "<font size=11>123 Shopping Street<br/>"
                     "Tamil Nadu, India - 620001<br/>"
                     "Phone: +91 1234567890<br/>"
                     "Email: support@trumpkart.com<br/>"
                     "GSTIN: 22AAAAA0000A1Z5</font>", 
                     normal_style)
        ]
    ]
    
    invoice_info_table = Table(invoice_info_data, colWidths=[3.4 * inch, 3.4 * inch])
    invoice_info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),  # Increased
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(invoice_info_table)
    elements.append(Spacer(1, 0.3 * inch))  # Increased spacing
    
    # Billing & Shipping Address - LARGER
    address = order.address
    address_data = [
        [
            Paragraph("<b>BILL TO:</b>", heading_style),
            Paragraph("<b>SHIP TO:</b>", heading_style)
        ],
        [
            Paragraph(f"<font size=11><b>{address.name}</b><br/>"
                     f"{address.house}, {address.area}<br/>"
                     f"{address.city}, {address.state} - {address.zipcode}<br/>"
                     f"Phone: {address.phone}</font>", 
                     normal_style),
            
            Paragraph(f"<font size=11><b>{address.name}</b><br/>"
                     f"{address.house}, {address.area}<br/>"
                     f"{address.city}, {address.state} - {address.zipcode}<br/>"
                     f"Phone: {address.phone}</font>", 
                     normal_style)
        ]
    ]
    
    address_table = Table(address_data, colWidths=[3.4 * inch, 3.4 * inch])
    address_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),  # Increased
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(address_table)
    elements.append(Spacer(1, 0.3 * inch))  # Increased spacing
    
    # Order Items Table - LARGER
    elements.append(Paragraph("ORDER DETAILS", heading_style))
    elements.append(Spacer(1, 0.15 * inch))
    
    # Table header
    items_data = [['#', 'Product Name', 'Vendor', 'Qty', 'Unit Price', 'Amount']]
    
    # Calculate items
    order_items = OrderItem.objects.filter(order=order)
    subtotal = 0
    
    for idx, item in enumerate(order_items, 1):
        item_total = float(item.quantity) * float(item.price)
        subtotal += item_total
        
        vendor_name = str(item.Product.vendor) if hasattr(item.Product, 'vendor') else 'TrumpKart'
        
        items_data.append([
            str(idx),
            item.Product.name[:40],  # Allow longer names
            vendor_name[:20],
            str(item.quantity),
            f"Rs.{item.price:,.2f}",
            f"Rs.{item_total:,.2f}"
        ])
    
    # Add summary rows
    items_data.extend([
        ['', '', '', '', 'Subtotal:', f"Rs.{subtotal:,.2f}"],
        ['', '', '', '', 'Shipping:', 'Rs.0.00'],
    ])
    
    # Create table with adjusted sizing
    items_table = Table(items_data, colWidths=[0.4*inch, 2.5*inch, 1.3*inch, 0.6*inch, 1.2*inch, 1*inch])
    
    # Style the table with LARGER fonts and padding
    items_table.setStyle(TableStyle([
        # Header style
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),  # Increased from 10
        ('TOPPADDING', (0, 0), (-1, 0), 12),  # Increased
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Body style
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -3), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),  # Increased from 10
        ('TOPPADDING', (0, 1), (-1, -1), 10),  # Increased
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        
        # Grid
        ('GRID', (0, 0), (-1, -3), 0.5, colors.HexColor('#e5e7eb')),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#667eea')),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -3), [colors.white, colors.HexColor('#f9fafb')]),
        
        # Summary section styling
        ('FONTNAME', (4, -2), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (4, -2), (-1, -1), 11),
        ('LINEABOVE', (4, -2), (-1, -2), 1, colors.HexColor('#e5e7eb')),
    ]))
    
    elements.append(items_table)
    elements.append(Spacer(1, 0.25 * inch))  # Increased spacing
    
    # Grand Total - LARGER
    total_data = [['TOTAL AMOUNT', f"Rs.{order.total_cost:,.2f}"]]
    total_table = Table(total_data, colWidths=[5.8 * inch, 1.2 * inch])
    total_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#10b981')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 16),  # Increased from 14
        ('TOPPADDING', (0, 0), (-1, -1), 14),  # Increased
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(total_table)
    elements.append(Spacer(1, 0.35 * inch))  # Increased spacing
    
    # Terms and Conditions - LARGER
    elements.append(Paragraph("<b>Terms & Conditions:</b>", heading_style))
    elements.append(Spacer(1, 0.1 * inch))
    
    terms_style = ParagraphStyle(
        'TermsStyle',
        parent=normal_style,
        fontSize=11,
        leading=20,  # More line spacing
        leftIndent=15
    )
    
    terms = """
    • Products can be returned within 10 days of delivery<br/>
    • For any queries, contact our customer support<br/>
    • Please keep this invoice for warranty and return purposes<br/>
    • All prices are inclusive of applicable taxes
    """
    elements.append(Paragraph(terms, terms_style))
    elements.append(Spacer(1, 0.3 * inch))  # Increased spacing
    
    # Thank you note - LARGER
    thank_you_style = ParagraphStyle(
        'ThankYou',
        parent=styles['Normal'],
        fontSize=15,  # Increased from 13
        textColor=colors.HexColor('#667eea'),
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceAfter=8,  # Increased
        spaceBefore=10
    )
    
    thank_you_subtitle = ParagraphStyle(
        'ThankYouSubtitle',
        parent=styles['Normal'],
        fontSize=12,  # Increased from 10
        textColor=colors.grey,
        alignment=TA_CENTER,
        leading=18
    )
    
    elements.append(Paragraph("Thank you for shopping with TrumpKart!", thank_you_style))
    elements.append(Paragraph("We appreciate your business and look forward to serving you again.", thank_you_subtitle))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF value
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
    if request.headers.get('X-requested-with') == 'XMLHttpRequest':
        if request.user.is_authenticated:
            data = json.loads(request.body)  # Fixed: json.loads() not json.load()
            product_qty = int(data['product_qty'])
            Product_id = data['pid']
            
            try:
                product_status = product.objects.get(id=Product_id)
            except product.DoesNotExist:
                return JsonResponse({'status': 'Product not found'}, status=404)
               
            if product_status:
                # Check if product already exists in cart
                existing_cart = Cart.objects.filter(user=request.user, Product_id=Product_id).first()
                
                if existing_cart:
                    # Product already in cart - update quantity
                    new_quantity = existing_cart.product_qty + product_qty
                    
                    # Check if enough stock available for the new quantity
                    if product_status.quantity >= new_quantity:
                        existing_cart.product_qty = new_quantity
                        existing_cart.save()
                        
                        # Get updated cart count
                        cart_count = Cart.objects.filter(user=request.user).count()
                        
                        return JsonResponse({
                            'status': 'Product quantity updated in cart',
                            'cart_count': cart_count,
                            'is_new': False
                        }, status=200)
                    else:
                        return JsonResponse({
                            'status': 'Not enough stock available',
                            'cart_count': Cart.objects.filter(user=request.user).count()
                        }, status=200)
                else:
                    # New product - add to cart
                    if product_status.quantity >= product_qty:
                        Cart.objects.create(
                            user=request.user,
                            Product_id=Product_id,
                            product_qty=product_qty
                        )
                        
                        # Get updated cart count
                        cart_count = Cart.objects.filter(user=request.user).count()
                        
                        return JsonResponse({
                            'status': 'Product added to cart successfully',
                            'cart_count': cart_count,
                            'is_new': True
                        }, status=200)
                    else:
                        return JsonResponse({
                            'status': 'Product stock not available',
                            'cart_count': Cart.objects.filter(user=request.user).count()
                        }, status=200)
        else:
            return JsonResponse({'status': 'Login to add to cart'}, status=401)
    else:
        return JsonResponse({'status': 'Invalid Access'}, status=400)
    
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
                        # Get current wishlist count
                        wish_count = favourite.objects.filter(user=request.user).count()
                        
                        return JsonResponse({
                            'status': 'Product already in your wishlist',
                            'wish_count': wish_count
                        }, status=200)
                    else:
                        # Add to favourites
                        favourite.objects.create(user=request.user, Product_id=Product_id)
                        
                        # Get updated wishlist count
                        wish_count = favourite.objects.filter(user=request.user).count()
                        
                        return JsonResponse({
                            'status': 'Product added to wishlist successfully',
                            'wish_count': wish_count
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
   
def removefavrt(request, fid):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAX request
        try:
            favrtitem = favourite.objects.get(id=fid, user=request.user)
            favrtitem.delete()
            
            # Get updated wishlist count
            wish_count = favourite.objects.filter(user=request.user).count()
            
            return JsonResponse({
                'status': 'Item removed from wishlist successfully',
                'wish_count': wish_count
            }, status=200)
        except favourite.DoesNotExist:
            return JsonResponse({
                'status': 'Item not found'
            }, status=404)
    else:
        # Regular request (keep existing functionality)
        favrtitem = favourite.objects.get(id=fid)
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
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user.id).count()
        wish_count = favourite.objects.filter(user=request.user.id).count()
        order_count = Order.objects.filter(user=request.user.id).count()
    else:
        cart_count = 0
        wish_count = 0
        order_count = 0
    
    hot_product = product.objects.filter(trending=1)
    
    if(category.objects.filter(name=cname, status=0)):
        if(product.objects.filter(name=pname, status=0)):
            products = product.objects.filter(name=pname, status=0).first()
            return render(request, 'Shop/products/products_detail.html', {
                "products": products, 
                "hot_product": hot_product,
                "cart_count": cart_count,
                "wish_count": wish_count,
                "order_count": order_count,
                "is_authenticated": request.user.is_authenticated 
            })
        else:
            messages.warning(request, "No Such Product Found")
            return redirect('collectionpage') 
    else:
        messages.warning(request, "No Such Category Found")
        return redirect('collectionpage')
            

def searchview(request):
    user = request.user if request.user.is_authenticated else None

    cart_count = Cart.objects.filter(user=user).count() if user else 0
    wish_count = favourite.objects.filter(user=user).count() if user else 0
    order_count = Order.objects.filter(user=user).count() if user else 0

    query = request.GET.get('q', '').strip().lower()

    categories = category.objects.none()
    products = product.objects.none()

    if query:
        words = query.split()

        cat_q = Q()
        prod_q = Q()

        for word in words:
            # Match word start anywhere in name
            regex = rf'(^|\s){re.escape(word)}'
            cat_q &= Q(name__iregex=regex) if cat_q else Q(name__iregex=regex)
            prod_q &= Q(name__iregex=regex) if prod_q else Q(name__iregex=regex)

        categories = category.objects.filter(cat_q).distinct()
        products = product.objects.filter(prod_q).distinct()

    context = {
        'categories': categories,
        'products': products,
        'cart_count': cart_count,
        'wish_count': wish_count,
        'order_count': order_count
    }

    return render(request, 'Shop/search.html', context)



def aboutview(request):
    cart_count = Cart.objects.filter(user=request.user.id).count()
    wish_count = favourite.objects.filter(user=request.user.id).count()
    order_count = Order.objects.filter(user=request.user.id).count()
    
    if request.user.is_authenticated:
        fav = favourite.objects.filter(user=request.user)
        
        context = {
            "cart_count": cart_count,
            "wish_count": wish_count,
            "order_count": order_count,
        }
    
    
    return render(request,'Shop/about.html', context)


def privacyview(request):
    cart_count = Cart.objects.filter(user=request.user.id).count()
    wish_count = favourite.objects.filter(user=request.user.id).count()
    order_count = Order.objects.filter(user=request.user.id).count()
    
    if request.user.is_authenticated:
        fav = favourite.objects.filter(user=request.user)
        
        context = {
            "cart_count": cart_count,
            "wish_count": wish_count,
            "order_count": order_count,
        }
    return render(request,'Shop/privacy.html', context)


def faqview (request):
    cart_count = Cart.objects.filter(user=request.user.id).count()
    wish_count = favourite.objects.filter(user=request.user.id).count()
    order_count = Order.objects.filter(user=request.user.id).count()
    
    if request.user.is_authenticated:
        fav = favourite.objects.filter(user=request.user)
        
        context = {
            "cart_count": cart_count,
            "wish_count": wish_count,
            "order_count": order_count,
        }
    return render(request, 'Shop/FAQ.html', context)
 
 
def supportView(request):
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()
        wish_count = favourite.objects.filter(user=request.user).count()
        order_count = Order.objects.filter(user=request.user).count()
    else:
        cart_count = 0
        wish_count = 0
        order_count = 0
    
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
                ['kishorehitter1995@gmail.com'],
                fail_silently=False,
            )
            form= supportForm()
            return JsonResponse({'status':'success', 'message':'Your issue has been Sent Successfully'})
        else:
            return JsonResponse({'status':'error', 'message':'Error in Reporting the Issue Please try again'})
    else:
        form =supportForm()
        context = {
        'form': form,
        'selected_content': selected_content,
        'cart_count': cart_count,
        'wish_count': wish_count,
        'order_count': order_count
    }
    return render(request,'Shop/mail.html', context)