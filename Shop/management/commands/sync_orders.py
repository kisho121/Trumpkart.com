from django.core.management.base import BaseCommand
from Shop.signals import sync_all_existing_orders
from Shop.services.google_sheets_service import get_sheets_service

class Command(BaseCommand):
    help = 'Sync all existing orders to Google Sheets'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear all data rows before syncing')
        parser.add_argument('--prod', action='store_true', help='Target production sheets')

    def handle(self, *args, **options):
        from decouple import config
        from django.conf import settings

        if options['prod'] or not settings.DEBUG:
            settings.MASTER_SHEET_ID = config('PROD_MASTER_SHEET_ID')
            settings.DEALER_SHEET_ID = config('PROD_DEALER_SHEET_ID')
            settings.DELIVERY_SHEET_ID = config('PROD_DELIVERY_SHEET_ID')
            self.stdout.write(self.style.WARNING('Targeting PRODUCTION sheets...'))
            
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data rows...'))
            service = get_sheets_service()
            if service:
                for sheet_type, spreadsheet in [
                    ('master', service.master_spreadsheet),
                    ('dealer', service.dealer_spreadsheet),
                    ('delivery', service.delivery_spreadsheet),
                ]:
                    ws = spreadsheet.worksheet('Sheet1')
                    all_rows = ws.get_all_values()
                    if len(all_rows) > 1:  # keep header row
                        ws.delete_rows(2, len(all_rows))  # delete from row 2 onwards
                        self.stdout.write(self.style.SUCCESS(f'✅ Cleared {sheet_type} sheet'))
            else:
                self.stdout.write(self.style.ERROR('❌ Failed to connect'))
                return

        self.stdout.write(self.style.WARNING('Starting order sync to Google Sheets...'))
        try:
            count = sync_all_existing_orders()
            if count:
                self.stdout.write(self.style.SUCCESS(f'✅ Successfully synced {count} order items!'))
            else:
                self.stdout.write(self.style.ERROR('❌ Failed to sync orders.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))