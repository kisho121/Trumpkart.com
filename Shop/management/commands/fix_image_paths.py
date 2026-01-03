import os
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from Shop.models import product, carousel  # Use lowercase

class Command(BaseCommand):
    help = 'Download images from Cloudinary and convert to local paths'

    def handle(self, *args, **options):
        # Temporarily configure Cloudinary to download images
        import cloudinary
        cloudinary.config(
            cloud_name=input("Enter CLOUDINARY_CLOUD_NAME: "),
            api_key=input("Enter CLOUDINARY_API_KEY: "),
            api_secret=input("Enter CLOUDINARY_API_SECRET: ")
        )
        
        media_root = settings.MEDIA_ROOT
        os.makedirs(media_root, exist_ok=True)
        
        # Fix products
        products = product.objects.all()
        self.stdout.write(f'Processing {products.count()} products...')
        
        for prod in products:
            if hasattr(prod.image, 'public_id'):  # It's a CloudinaryResource
                try:
                    # Get Cloudinary URL
                    cloudinary_url = prod.image.url
                    public_id = prod.image.public_id
                    
                    # Determine local path
                    # Example: "products/image_abc" -> "products/image_abc.jpg"
                    local_path = public_id
                    if not local_path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                        local_path += '.jpg'  # Default to jpg
                    
                    full_local_path = os.path.join(media_root, local_path)
                    
                    # Create directory if needed
                    os.makedirs(os.path.dirname(full_local_path), exist_ok=True)
                    
                    # Download image
                    self.stdout.write(f'Downloading: {cloudinary_url}')
                    response = requests.get(cloudinary_url, timeout=10)
                    response.raise_for_status()
                    
                    with open(full_local_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Update database with local path
                    prod.image = local_path
                    prod.save()
                    
                    self.stdout.write(self.style.SUCCESS(f'✓ {prod.name} -> {local_path}'))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ Failed {prod.name}: {e}'))
        
        # Fix carousel images
        carousels = carousel.objects.all()
        self.stdout.write(f'\nProcessing {carousels.count()} carousel images...')
        
        for car in carousels:
            if hasattr(car.image, 'public_id'):
                try:
                    cloudinary_url = car.image.url
                    public_id = car.image.public_id
                    
                    local_path = public_id
                    if not local_path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                        local_path += '.jpg'
                    
                    full_local_path = os.path.join(media_root, local_path)
                    os.makedirs(os.path.dirname(full_local_path), exist_ok=True)
                    
                    self.stdout.write(f'Downloading: {cloudinary_url}')
                    response = requests.get(cloudinary_url, timeout=10)
                    response.raise_for_status()
                    
                    with open(full_local_path, 'wb') as f:
                        f.write(response.content)
                    
                    car.image = local_path
                    car.save()
                    
                    self.stdout.write(self.style.SUCCESS(f'✓ Carousel {car.id} -> {local_path}'))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ Failed carousel {car.id}: {e}'))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Migration complete!'))
        self.stdout.write('All images downloaded and database updated.')