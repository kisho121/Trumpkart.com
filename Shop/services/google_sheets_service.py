# Shop/services/google_sheets_service.py
# Service for managing 3 SEPARATE Google Sheets

import gspread
from google.oauth2.service_account import Credentials
from django.conf import settings
import os
import pytz

class GoogleSheetsService:
    """
    Service to manage 3 separate Google Sheets for different roles
    """
    
    def __init__(self):
        # Define the required scopes
        self.scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        
       # Authenticate with Google using credentials dict from env
        self.creds = Credentials.from_service_account_info(
            settings.GOOGLE_SHEETS_CREDENTIALS,  # ✅ dict loaded from env
            scopes=self.scope
        )
        self.client = gspread.authorize(self.creds)
        
        # Get the three separate sheet IDs from settings
        self.master_sheet_id = settings.MASTER_SHEET_ID
        self.dealer_sheet_id = settings.DEALER_SHEET_ID
        self.delivery_sheet_id = settings.DELIVERY_SHEET_ID
        
        
        # Open all three spreadsheets
        try:
            self.master_spreadsheet = self.client.open_by_key(self.master_sheet_id)
            self.dealer_spreadsheet = self.client.open_by_key(self.dealer_sheet_id)
            self.delivery_spreadsheet = self.client.open_by_key(self.delivery_sheet_id)
        except Exception as e:
            print(f"Error opening spreadsheets: {e}")
            raise
    
    def get_worksheet(self, sheet_type='master', sheet_name='Sheet1'):
        """
        Get worksheet from the appropriate spreadsheet
        
        Args:
            sheet_type: 'master', 'delivery', or 'dealer'
            sheet_name: Name of the worksheet tab
        """
        if sheet_type == 'master':
            spreadsheet = self.master_spreadsheet
        elif sheet_type == 'dealer':
            spreadsheet = self.dealer_spreadsheet
        elif sheet_type == 'delivery':
            spreadsheet = self.delivery_spreadsheet
        else:
            raise ValueError(f"Invalid sheet_type: {sheet_type}")
        
        try:
            return spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            return spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
    
    def convert_to_local_time(self, utc_datetime):
        """
        Convert UTC datetime to Indian Standard Time
        """
        ist = pytz.timezone('Asia/Kolkata')
        
        if utc_datetime.tzinfo is None:
            utc_datetime = pytz.utc.localize(utc_datetime)
        
        local_time = utc_datetime.astimezone(ist)
        return local_time.strftime('%Y-%m-%d %I:%M:%S %p')
    
    def append_row(self, data, sheet_type='master', sheet_name='Sheet1'):
        """
        Append a row to the specified sheet
        """
        worksheet = self.get_worksheet(sheet_type, sheet_name)
        return worksheet.append_row(data, value_input_option='USER_ENTERED')
    
    def create_headers(self, headers, sheet_type='master', sheet_name='Sheet1'):
        """
        Create header row if sheet is empty
        """
        worksheet = self.get_worksheet(sheet_type, sheet_name)
        
        try:
            first_row = worksheet.row_values(1)
            if first_row and len(first_row) > 0:
                return
        except:
            pass
        
        worksheet.update('A1', [headers])
        
        # Format headers
        worksheet.format('A1:Z1', {
            "textFormat": {"bold": True, "fontSize": 11},
            "backgroundColor": {"red": 0.2, "green": 0.5, "blue": 0.8},
            "horizontalAlignment": "CENTER"
        })
    
    def setup_all_sheets(self):
        """
        Setup all three separate sheets with proper headers
        """
        # === MASTER SHEET (Admin Only - Full Details) ===
        master_headers = [
            'Order ID.',
            'Order No',
            'Order Date',
            'Customer Name',
            'Customer Email',
            'Phone',
            'Product Name',
            'Quantity',
            'Unit Price (₹)',
            'Item Total (₹)',
            'Payment Type',
            'Payment Status',
            'Order Status',
            'Full Address',
            'City',
            'State',
            'Country',
            'Zipcode'
        ]
        self.create_headers(master_headers, sheet_type='master', sheet_name='Sheet1')
        
        
        # === DEALER SHEET (For Suppliers - No Customer Info) ===
        dealer_headers = [
            'Order ID.',
            'Order Date',
            'Product Name',
            'Quantity',
            'Delivery City',
            'Order Status'
        ]
        self.create_headers(dealer_headers, sheet_type='dealer', sheet_name='Sheet1')

        # === DELIVERY SHEET (For Delivery Personnel - No Pricing) ===
        delivery_headers = [
            'Order ID.',
            'Order Date',
            'Customer Name',
            'Phone',
            'Full Address',
            'City',
            'Product',
            'Quantity',
            'COD Amount',      # Only for COD orders
            'Order Status'
        ]
        self.create_headers(delivery_headers, sheet_type='delivery', sheet_name='Sheet1')
    
    def find_and_update_status(self, order_number, new_status, payment_status, sheet_type='master', sheet_name='Sheet1'):
        """
        Find order by order number and update status
        """
        worksheet = self.get_worksheet(sheet_type, sheet_name)
        all_values = worksheet.get_all_values()
        
        rows_updated = 0
        for row_idx, row in enumerate(all_values[1:], start=2):
            if len(row) > 0 and row[0] == order_number:  # Column A is Order No.
                
                if sheet_type == 'master':
                    # Master sheet: Update both payment status (col 12) and order status (col 13)
                    worksheet.update_cell(row_idx, 12, payment_status)
                    worksheet.update_cell(row_idx, 13, new_status)
                    
                elif sheet_type == 'dealer':
                    # Dealer sheet: Update order status (col 6)
                    worksheet.update_cell(row_idx, 6, new_status)

                elif sheet_type == 'delivery':
                    # Delivery sheet: Update order status (col 10)
                    worksheet.update_cell(row_idx, 10, new_status)
                
                rows_updated += 1
        
        return rows_updated


# Helper function
def get_sheets_service():
    """
    Factory function to get GoogleSheetsService instance
    """
    try:
        return GoogleSheetsService()
    except Exception as e:
        print(f"Error initializing Google Sheets Service: {e}")
        return None