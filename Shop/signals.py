# Shop/signals.py
# Sync to 3 SEPARATE Google Sheets

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order, OrderItem
from .services.google_sheets_service import get_sheets_service
import logging

logger = logging.getLogger(__name__)

_synced_items = set()

@receiver(post_save, sender=OrderItem)
def sync_orderitem_to_all_sheets(sender, instance, created, **kwargs):
    """
    Sync each order item to all THREE SEPARATE sheets
    """
    if not created:
        return
    
    item_key = f"order_{instance.order.id}_item_{instance.id}"
    
    if item_key in _synced_items:
        print(f"⏭️  Item already synced: {item_key}")
        return
    
    try:
        order = instance.order
        address = order.address
        
        print(f"\n{'='*60}")
        print(f"🔄 Syncing OrderItem #{instance.id} from Order #{order.id}")
        print(f"   Product: {instance.Product.name}")
        print(f"   Quantity: {instance.quantity}")
        print(f"{'='*60}")
        
        sheets = get_sheets_service()
        
        if not sheets:
            logger.error("Failed to initialize Google Sheets service")
            print("❌ Failed to get sheets service")
            return
        
        # Convert time to IST
        local_time = sheets.convert_to_local_time(order.created_at)
        date_only = local_time.split()[0]  # Just the date part
        
        # Order identifiers
        order_number = order.final_order_id if order.final_order_id else f"ORD-{order.id}"
        order_id = str(order.id)
        
        # Determine payment status for MASTER sheet using payment_status field
        is_cod = order.payment_method.upper() == 'COD'
        
        if is_cod:
            if order.payment_status == Order.PAYMENT_PENDING:
                master_payment_status = 'COD - Not Received'
            elif order.payment_status == Order.PAYMENT_COD_COLLECTED:
                master_payment_status = 'COD - Received'
            else:
                master_payment_status = 'COD - Confirmed'
        else:  # Razorpay/Online
            if order.payment_status == Order.PAYMENT_COMPLETED:
                master_payment_status = 'Paid Online'
            elif order.payment_status == Order.PAYMENT_REFUNDED:
                master_payment_status = 'Refunded'
            else:
                master_payment_status = 'Payment Pending'
        
        # === 1. MASTER SHEET (Admin - Full Details) ===
        master_data = [
            order_id,                                                    # Order ID
            order_number,                                                # Order No.
            local_time,                                                  # Order Date (Full)
            address.name if address else order.user.username,           # Customer Name
            address.email if address else order.user.email,             # Customer Email
            address.phone if address else 'N/A',                        # Phone
            instance.Product.name,                                       # Product Name
            str(instance.quantity),                                      # Quantity
            f"₹{float(instance.price):.2f}",                            # Unit Price
            f"₹{float(instance.price * instance.quantity):.2f}",        # Item Total
            order.payment_method,                                        # Payment Type
            master_payment_status,                                       # Payment Status
            order.get_status_display(),                                  # Order Status
            f"{address.house}, {address.area}, {address.address}" if address else 'N/A',
            address.city if address else 'N/A',
            address.state if address else 'N/A',
            address.country if address else 'India',
            address.zipcode if address else 'N/A',
        ]
        
        sheets.append_row(master_data, sheet_type='master', sheet_name='Sheet1')
        print(f"   ✅ Synced to MASTER Sheet (Admin)")
        
        # === 2. DEALER SHEET (Suppliers - Only Product Info) ===
        dealer_data = [
            order_number,                                                # Order No.
            date_only,                                                   # Order Date
            instance.Product.name,                                       # Product Name
            str(instance.quantity),                                      # Quantity
            address.city if address else 'N/A',                         # Delivery City
            order.get_status_display(),                                  # Order Status
        ]
        
        sheets.append_row(dealer_data, sheet_type='dealer', sheet_name='Sheet1')
        print(f"   ✅ Synced to DEALER Sheet")

         # === 3. DELIVERY SHEET (Delivery Personnel - No Prices for Online Orders) ===
        # Only show COD amount if it's COD payment
        cod_amount = f"₹{float(instance.price * instance.quantity):.2f}" if is_cod else "Paid Online"
        
        delivery_data = [
            order_number,                                                # Order No.
            date_only,                                                   # Order Date
            address.name if address else order.user.username,           # Customer Name
            address.phone if address else 'N/A',                        # Phone
            f"{address.house}, {address.area}, {address.address}" if address else 'N/A',
            address.city if address else 'N/A',
            instance.Product.name,                                       # Product
            str(instance.quantity),                                      # Quantity
            cod_amount,                                                  # COD Amount (or "Paid Online")
            order.get_status_display(),                                  # Order Status
        ]
        
        sheets.append_row(delivery_data, sheet_type='delivery', sheet_name='Sheet1')
        print(f"   ✅ Synced to DELIVERY Sheet")
        
        _synced_items.add(item_key)
        
        logger.info(f"Successfully synced OrderItem #{instance.id} to all 3 separate sheets")
        print(f"🎉 Successfully synced to ALL 3 SEPARATE SHEETS")
        print(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Error syncing OrderItem #{instance.id}: {str(e)}")
        print(f"❌ Failed to sync: {str(e)}")
        import traceback
        traceback.print_exc()


# Track order status changes
@receiver(pre_save, sender=Order)
def track_order_status_change(sender, instance, **kwargs):
    """
    Track when order status changes
    """
    if instance.pk:
        try:
            old_order = Order.objects.get(pk=instance.pk)
            instance._status_changed = old_order.status != instance.status
            instance._old_status = old_order.status
        except Order.DoesNotExist:
            instance._status_changed = False
    else:
        instance._status_changed = False


@receiver(post_save, sender=Order)
def update_order_status_in_sheets(sender, instance, created, **kwargs):
    """
    Update order status in all 3 separate sheets when admin changes it
    """
    if created:
        print(f"\n📦 NEW ORDER CREATED:")
        print(f"   Order Number: {instance.final_order_id}")
        print(f"   Order ID: #{instance.id}")
        print(f"   Customer: {instance.user.username}")
        print(f"   Status: {instance.get_status_display()}")
        print(f"   Items will sync to 3 separate sheets automatically\n")
        return
    
    if not getattr(instance, '_status_changed', False):
        return
    
    try:
        print(f"\n{'='*60}")
        print(f"📝 ORDER STATUS UPDATE DETECTED")
        print(f"   Order #{instance.id}")
        print(f"   Old Status: {Order.STATUS_CHOICES[instance._old_status][1]}")
        print(f"   New Status: {instance.get_status_display()}")
        print(f"{'='*60}")
        
        sheets = get_sheets_service()
        if not sheets:
            print("❌ Failed to connect to sheets")
            return
        
        order_number = instance.final_order_id if instance.final_order_id else f"ORD-{instance.id}"
        new_status = instance.get_status_display()
        
        # Determine payment status based on payment_status field
        is_cod = instance.payment_method.upper() == 'COD'
        
        if is_cod:
            if instance.payment_status == Order.PAYMENT_PENDING:
                payment_status = 'COD - Not Received'
            elif instance.payment_status == Order.PAYMENT_COD_COLLECTED:
                payment_status = 'COD - Received'
            else:
                payment_status = 'COD - Confirmed'
        else:
            if instance.payment_status == Order.PAYMENT_COMPLETED:
                payment_status = 'Paid Online'
            elif instance.payment_status == Order.PAYMENT_REFUNDED:
                payment_status = 'Refunded'
            else:
                payment_status = 'Payment Pending'
        
        # Update all three separate sheets
        print("\n   Updating all 3 sheets...")
        
        # Update Master Sheet
        master_updated = sheets.find_and_update_status(
            order_number, 
            new_status, 
            payment_status, 
            sheet_type='master'
        )
        if master_updated > 0:
            print(f"   ✅ Updated {master_updated} rows in MASTER Sheet")
        
        
        # Update Dealer Sheet
        dealer_updated = sheets.find_and_update_status(
            order_number, 
            new_status, 
            payment_status, 
            sheet_type='dealer'
        )
        if dealer_updated > 0:
            print(f"   ✅ Updated {dealer_updated} rows in DEALER Sheet")

         # Update Delivery Sheet
        delivery_updated = sheets.find_and_update_status(
            order_number, 
            new_status, 
            payment_status, 
            sheet_type='delivery'
        )
        if delivery_updated > 0:
            print(f"   ✅ Updated {delivery_updated} rows in DELIVERY Sheet")
        
        logger.info(f"Updated Order #{instance.id} status in all 3 sheets")
        print(f"🎉 Status update complete in all 3 sheets!")
        print(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Error updating Order #{instance.id} status: {str(e)}")
        print(f"❌ Failed to update status: {str(e)}")
        import traceback
        traceback.print_exc()


# One-time sync function
def sync_all_existing_orders():
    """
    Sync all existing orders to all 3 separate sheets
    """
    from .models import Order
    
    sheets = get_sheets_service()
    if not sheets:
        print("❌ Failed to connect to Google Sheets")
        return 0
    
    print("📋 Setting up all 3 separate sheets...")
    sheets.setup_all_sheets()
    
    orders = Order.objects.all().order_by('-created_at')
    total_items = 0
    
    print(f"\n📊 Syncing {orders.count()} orders to 3 separate sheets...")
    print(f"{'='*60}")
    
    for order in orders:
        try:
            address = order.address
            order_items = order.order_items.all()
            
            if not order_items.exists():
                print(f"⚠️  Order #{order.id} has no items - skipping")
                continue
            
            order_number = order.final_order_id if order.final_order_id else f"ORD-{order.id}"
            order_id = str(order.id)
            local_time = sheets.convert_to_local_time(order.created_at)
            date_only = local_time.split()[0]
            
            is_cod = order.payment_method.upper() == 'COD'
            
            # Determine payment status based on payment_status field
            if is_cod:
                if order.payment_status == Order.PAYMENT_PENDING:
                    master_payment_status = 'COD - Not Received'
                elif order.payment_status == Order.PAYMENT_COD_COLLECTED:
                    master_payment_status = 'COD - Received'
                else:
                    master_payment_status = 'COD - Confirmed'
            else:
                if order.payment_status == Order.PAYMENT_COMPLETED:
                    master_payment_status = 'Paid Online'
                elif order.payment_status == Order.PAYMENT_REFUNDED:
                    master_payment_status = 'Refunded'
                else:
                    master_payment_status = 'Payment Pending'
            
            for item in order_items:
                # Master Sheet
                master_data = [
                    order_number, order_id, local_time,
                    address.name if address else order.user.username,
                    address.email if address else order.user.email,
                    address.phone if address else 'N/A',
                    item.Product.name, str(item.quantity),
                    f"₹{float(item.price):.2f}",
                    f"₹{float(item.price * item.quantity):.2f}",
                    order.payment_method, master_payment_status,
                    order.get_status_display(),
                    f"{address.house}, {address.area}, {address.address}" if address else 'N/A',
                    address.city if address else 'N/A',
                    address.state if address else 'N/A',
                    address.country if address else 'India',
                    address.zipcode if address else 'N/A',
                ]
                sheets.append_row(master_data, sheet_type='master', sheet_name='Sheet1')
                
                # Dealer Sheet
                dealer_data = [
                    order_number, date_only,
                    item.Product.name, str(item.quantity),
                    address.city if address else 'N/A',
                    order.get_status_display(),
                ]
                sheets.append_row(dealer_data, sheet_type='dealer', sheet_name='Sheet1')

                # Delivery Sheet
                cod_amount = f"₹{float(item.price * item.quantity):.2f}" if is_cod else "Paid Online"
                delivery_data = [
                    order_number, date_only,
                    address.name if address else order.user.username,
                    address.phone if address else 'N/A',
                    f"{address.house}, {address.area}, {address.address}" if address else 'N/A',
                    address.city if address else 'N/A',
                    item.Product.name, str(item.quantity),
                    cod_amount, order.get_status_display(),
                ]
                sheets.append_row(delivery_data, sheet_type='delivery', sheet_name='Sheet1')
                
                total_items += 1
            
            print(f"✅ Order #{order.id} synced to all 3 sheets ({order_items.count()} items)")
            
        except Exception as e:
            print(f"❌ Error syncing Order #{order.id}: {e}")
            continue
    
    print(f"{'='*60}")
    print(f"✅ Sync complete! Synced {total_items} items to 3 separate sheets")
    print(f"{'='*60}")
    
    return total_items