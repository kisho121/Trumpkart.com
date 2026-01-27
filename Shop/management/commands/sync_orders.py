from django.core.management.base import BaseCommand
from Shop.signals import sync_all_existing_orders

class Command(BaseCommand):
    help = 'Sync all existing orders to Google Sheets'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting order sync to Google Sheets...'))
        
        try:
            count = sync_all_existing_orders()
            
            if count:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Successfully synced {count} order items to Google Sheets!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Failed to sync orders. Check your configuration.')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {str(e)}')
            )