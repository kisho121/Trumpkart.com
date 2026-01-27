from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Shop'
    
    def ready(self):
        """
        Import signals when Django starts
        This ensures signals are registered and active
        """
        import Shop.signals
        print("✅ TrumpKart Google Sheets sync is active")