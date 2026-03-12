from django.contrib import admin
from django.utils import timezone
from django.http import HttpResponse
from django.utils.html import format_html
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
from django.core.files.base import ContentFile
from .models import *
import requests
import tempfile
import os

# ============================================================================
# ORDER ADMIN
# ============================================================================

class OrderAdmin(admin.ModelAdmin):
    list_display = ['final_order_id', 'user', 'get_status_display', 'get_payment_status_display', 'created_at', 'total_cost', 'label_link']
    list_filter = ['status', 'payment_method', 'payment_status']
    search_fields = ['final_order_id', 'user__username', 'user__email', 'awb_code']
    readonly_fields = ['created_at', 'packed_at', 'shipped_at', 'out_for_delivery_at',
                      'delivered_at', 'canceled_at', 'return_requested_at', 
                      'return_approved_at', 'returned_at', 'refunded_at',
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
    
    def label_link(self, obj):
        if hasattr(obj, 'shipping_label'):
            label = obj.shipping_label
            return format_html(
                '<a href="/admin/Shop/shippinglabel/{}/change/" style="color: #667eea; font-weight: bold;">📦 {}</a>',
                label.id,
                label.tracking_number
            )
        return format_html('<span style="color: #999;">No label</span>')
    label_link.short_description = 'Shipping Label'
    
    def get_status_display(self, obj):
        return obj.get_status_display()
    get_status_display.short_description = 'Status'
    
    def get_payment_status_display(self, obj):
        return obj.get_payment_status_display()
    get_payment_status_display.short_description = 'Payment Status'
    
    def save_model(self, request, obj, form, change):
        if change:
            try:
                original = Order.objects.get(pk=obj.pk)
                if original.status != obj.status:
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
                pass
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


# ============================================================================
# SHIPPING LABEL ADMIN - WITH WORKING QR CODE
# ============================================================================

@admin.register(ShippingLabel)
class ShippingLabelAdmin(admin.ModelAdmin):
    list_display = ['tracking_number', 'order_id_display', 'customer_name', 'customer_phone', 'order_status', 'generated_at', 'print_status', 'download_label']
    list_filter = ['is_printed', 'generated_at', 'order__status', 'order__payment_method']
    search_fields = ['tracking_number', 'order__final_order_id', 'order__address__name', 'order__address__phone']
    readonly_fields = ['tracking_number', 'generated_at', 'qr_code_preview', 'printed_at', 'printed_by']
    actions = ['print_selected_labels', 'mark_as_printed', 'mark_as_not_printed', 'regenerate_labels']
    
    fieldsets = (
        ('Label Information', {'fields': ('tracking_number', 'order', 'generated_at')}),
        ('QR Code', {'fields': ('qr_code', 'qr_code_preview')}),
        ('Label PDF', {'fields': ('label_pdf',)}),
        ('Print Status', {'fields': ('is_printed', 'printed_at', 'printed_by')}),
    )
    
    def order_id_display(self, obj):
        return format_html('<a href="/admin/Shop/order/{}/change/">{}</a>', obj.order.id, obj.order.final_order_id)
    order_id_display.short_description = 'Order ID'
    
    def customer_name(self, obj):
        return obj.order.address.name
    customer_name.short_description = 'Customer'
    
    def customer_phone(self, obj):
        return obj.order.address.phone
    customer_phone.short_description = 'Phone'
    
    def order_status(self, obj):
        colors_map = {'PLACED': '#3b82f6', 'PACKED': '#8b5cf6', 'SHIPPED': '#6366f1', 'OUT_FOR_DELIVERY': '#f59e0b', 'DELIVERED': '#10b981', 'CANCELED': '#ef4444', 'RETURN_REQUESTED': '#f97316'}
        color = colors_map.get(obj.order.status, '#6b7280')
        return format_html('<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>', color, obj.order.get_status_display())
    order_status.short_description = 'Order Status'
    
    def print_status(self, obj):
        if obj.is_printed:
            return format_html('<span style="color: #10b981; font-weight: bold;">✓ Printed</span><br><span style="font-size: 11px; color: #6b7280;">{}</span>', obj.printed_at.strftime('%d %b %Y, %I:%M %p') if obj.printed_at else '')
        return format_html('<span style="color: #f59e0b; font-weight: bold;">⊘ Not Printed</span>')
    print_status.short_description = 'Print Status'
    
    def download_label(self, obj):
        if obj.label_pdf:
            return format_html('<a href="{}" class="button" style="background-color: #667eea; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 12px;">📥 Download</a>', obj.label_pdf.url)
        return format_html('<span style="color: #999;">No PDF</span>')
    download_label.short_description = 'Label'
    
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" style="max-width: 150px; max-height: 150px;"/>', obj.qr_code.url)
        return "No QR Code"
    qr_code_preview.short_description = 'QR Code Preview'
    
    def print_selected_labels(self, request, queryset):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="thermal_labels_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        
        buffer = BytesIO()
        label_width = 4 * inch
        label_height = 6 * inch
        c = canvas.Canvas(buffer, pagesize=(label_width, label_height))
        
        labels = list(queryset.order_by('generated_at'))
        
        for idx, shipping_label in enumerate(labels):
            if idx > 0:
                c.showPage()
            self.draw_thermal_label(c, shipping_label, label_width, label_height)
            shipping_label.mark_as_printed(user=request.user)
        
        c.save()
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        self.message_user(request, f"✓ {len(labels)} thermal labels ready to print!")
        return response
    print_selected_labels.short_description = "🖨️ Print Labels (Thermal Printer)"
    
    def mark_as_printed(self, request, queryset):
        updated = 0
        for label in queryset:
            if not label.is_printed:
                label.mark_as_printed(user=request.user)
                updated += 1
        self.message_user(request, f"✓ {updated} labels marked as printed")
    mark_as_printed.short_description = "✓ Mark as Printed"
    
    def mark_as_not_printed(self, request, queryset):
        updated = queryset.update(is_printed=False, printed_at=None, printed_by=None)
        self.message_user(request, f"✓ {updated} labels marked as not printed")
    mark_as_not_printed.short_description = "↺ Mark as NOT Printed"
    
    def regenerate_labels(self, request, queryset):
        from .views import generate_shipping_label_pdf
        count = 0
        errors = []
        for label in queryset:
            try:
                pdf_content = generate_shipping_label_pdf(label)
                filename = f"label_{label.order.final_order_id}.pdf"
                label.label_pdf.save(filename, ContentFile(pdf_content), save=True)
                count += 1
            except Exception as e:
                errors.append(f"{label.tracking_number}: {str(e)}")
        if count > 0:
            self.message_user(request, f"✓ {count} labels regenerated successfully")
        if errors:
            for error in errors[:5]:
                self.message_user(request, f"✗ Error: {error}", level='error')
    regenerate_labels.short_description = "🔄 Regenerate Label PDFs"
    
    def draw_thermal_label(self, c, shipping_label, width, height):
        """PERFECT label with QR code from Cloudinary"""
        print("\n" + "="*80)
        print("🚨 DRAWING LABEL START")
        print(f"Order: {shipping_label.order.final_order_id}")
        print(f"Has QR: {bool(shipping_label.qr_code)}")
        if shipping_label.qr_code:
            print(f"QR URL: {shipping_label.qr_code.url}")
        print("="*80 + "\n")
        
        order = shipping_label.order
        address = order.address
        
        # Border
        c.setStrokeColor(colors.black)
        c.setLineWidth(4)
        c.roundRect(0.08*inch, 0.08*inch, width-0.16*inch, height-0.16*inch, 15, stroke=1, fill=0)
        
        # Header
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 26)
        c.drawCentredString(width/2, height-0.48*inch, "TRUMPKART")
        c.setLineWidth(2.5)
        c.line(0.22*inch, height-0.68*inch, width-0.22*inch, height-0.68*inch)
        
        # Tracking + Badge
        y = height-0.92*inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.22*inch, y, "Tracking ID:")
        c.setFont("Helvetica", 10)
        c.drawString(0.22*inch, y-0.18*inch, shipping_label.tracking_number)
        
        badge_w, badge_h = 0.6*inch, 0.32*inch
        badge_x = width - badge_w - 0.22*inch
        badge_y = y - 0.12*inch
        c.setFillColor(colors.black)
        c.roundRect(badge_x, badge_y, badge_w, badge_h, 6, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(badge_x+badge_w/2, badge_y+0.1*inch, order.payment_method)
        
        # Barcode
        y -= 0.48*inch
        c.setFillColor(colors.black)
        try:
            from reportlab.graphics.barcode import code128
            barcode = code128.Code128(shipping_label.tracking_number, barHeight=0.6*inch, barWidth=1.3, humanReadable=False)
            barcode.drawOn(c, 0.25*inch, y-0.6*inch)
            y -= 0.88*inch
        except:
            y -= 0.48*inch
        
        # Order info
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.22*inch, y, f"Order: {order.final_order_id}")
        y -= 0.2*inch
        c.setFont("Helvetica", 9)
        c.drawString(0.22*inch, y, order.created_at.strftime('%d %B %Y'))
        y -= 0.38*inch
        
        # Address box
        box_h = 1.35*inch
        box_y = y - box_h
        c.setFillColor(colors.HexColor('#E8E8E8'))
        c.setStrokeColor(colors.HexColor('#D0D0D0'))
        c.setLineWidth(1.5)
        c.roundRect(0.18*inch, box_y, width-0.36*inch, box_h, 10, stroke=1, fill=1)
        
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.28*inch, y-0.18*inch, "SHIP TO:")
        c.setFont("Helvetica-Bold", 15)
        c.drawString(0.28*inch, y-0.42*inch, address.name[:26])
        
        c.setFont("Helvetica", 10)
        y_addr = y-0.65*inch
        for line in [f"{address.house}, {address.area}"[:36], f"{address.city}, {address.state} - {address.zipcode}"[:36], f"Phone: {address.phone}"]:
            c.drawString(0.28*inch, y_addr, line)
            y_addr -= 0.18*inch
        
        # Arrow + QR CODE
        bottom_y = 0.40*inch
        arrow_x = 0.35*inch
        arrow_y = bottom_y + 0.45*inch
        
        c.setStrokeColor(colors.black)
        c.setLineWidth(4.5)
        c.setFillColor(colors.white)
        arrow = c.beginPath()
        arrow.moveTo(arrow_x, arrow_y+0.18*inch)
        arrow.lineTo(arrow_x+0.42*inch, arrow_y+0.18*inch)
        arrow.lineTo(arrow_x+0.42*inch, arrow_y+0.28*inch)
        arrow.lineTo(arrow_x+0.58*inch, arrow_y)
        arrow.lineTo(arrow_x+0.42*inch, arrow_y-0.28*inch)
        arrow.lineTo(arrow_x+0.42*inch, arrow_y-0.18*inch)
        arrow.lineTo(arrow_x, arrow_y-0.18*inch)
        arrow.close()
        c.drawPath(arrow, stroke=1, fill=1)
        
        # QR CODE - DOWNLOAD FROM CLOUDINARY
        if shipping_label.qr_code:
            try:
                qr_size = 1.2*inch
                qr_x = width - qr_size - 0.28*inch
                qr_y = bottom_y
                
                qr_url = shipping_label.qr_code.url
                print(f"📥 Downloading QR from: {qr_url}")
                
                response = requests.get(qr_url, timeout=10)
                print(f"Status: {response.status_code}, Size: {len(response.content)} bytes")
                
                if response.status_code == 200:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                        tmp_file.write(response.content)
                        tmp_path = tmp_file.name
                    
                    print(f"Temp file: {tmp_path}")
                    c.drawImage(tmp_path, qr_x, qr_y, width=qr_size, height=qr_size, preserveAspectRatio=True)
                    
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                    
                    print("✅ QR CODE ADDED SUCCESSFULLY!")
                else:
                    print(f"❌ Failed to download QR: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"❌ QR code error: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("⚠️ No QR code for this label")
        
        # Footer
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor('#888888'))
        c.drawCentredString(width/2, 0.12*inch, "Handle with Care")
        
        print("🏁 DRAWING LABEL COMPLETE\n")


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
admin.site.register(Order, OrderAdmin)