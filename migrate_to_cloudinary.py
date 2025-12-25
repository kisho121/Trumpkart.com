# migrate_to_cloudinary.py
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Ecom.settings')
django.setup()

import cloudinary
import cloudinary.uploader
from pathlib import Path

# Import your models
from Shop.models import product, category, carousel

def migrate_images():
    """Upload all local images to Cloudinary"""
    
    print(f"\n{'='*60}")
    print(f"STARTING CLOUDINARY MIGRATION")
    print(f"{'='*60}\n")
    
    total_success = 0
    total_failed = 0
    total_skipped = 0
    
    # ===== MIGRATE CAROUSEL IMAGES =====
    print("\n[1/3] MIGRATING CAROUSEL IMAGES")
    print("-" * 60)
    
    carousels = carousel.objects.all()
    print(f"Found {carousels.count()} carousel images\n")
    
    for index, item in enumerate(carousels, 1):
        print(f"[{index}/{carousels.count()}] Processing carousel image")
        
        if not item.carousel_image:
            print(f"  ⊘ No image - skipping")
            total_skipped += 1
            continue
        
        try:
            if hasattr(item.carousel_image, 'path'):
                local_path = item.carousel_image.path
            else:
                print(f"  ⊘ Already on cloud - skipping")
                total_skipped += 1
                continue
            
            if not os.path.exists(local_path):
                print(f"  ✗ File not found: {local_path}")
                total_failed += 1
                continue
            
            filename = os.path.basename(local_path)
            print(f"  ↑ Uploading: {filename}")
            
            result = cloudinary.uploader.upload(
                local_path,
                folder="carousel",
                public_id=f"carousel_{item.id}_{Path(filename).stem}",
                overwrite=True,
                resource_type="auto"
            )
            
            item.carousel_image = result['secure_url']
            item.save()
            
            print(f"  ✓ Success: {result['secure_url']}")
            total_success += 1
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            total_failed += 1
    
    # ===== MIGRATE CATEGORY IMAGES =====
    print("\n[2/3] MIGRATING CATEGORY IMAGES")
    print("-" * 60)
    
    categories = category.objects.all()
    print(f"Found {categories.count()} categories\n")
    
    for index, cat in enumerate(categories, 1):
        print(f"[{index}/{categories.count()}] Processing: {cat.name}")
        
        if not cat.image:
            print(f"  ⊘ No image - skipping")
            total_skipped += 1
            continue
        
        try:
            if hasattr(cat.image, 'path'):
                local_path = cat.image.path
            else:
                print(f"  ⊘ Already on cloud - skipping")
                total_skipped += 1
                continue
            
            if not os.path.exists(local_path):
                print(f"  ✗ File not found: {local_path}")
                total_failed += 1
                continue
            
            filename = os.path.basename(local_path)
            print(f"  ↑ Uploading: {filename}")
            
            result = cloudinary.uploader.upload(
                local_path,
                folder="categories",
                public_id=f"category_{cat.id}_{Path(filename).stem}",
                overwrite=True,
                resource_type="auto"
            )
            
            cat.image = result['secure_url']
            cat.save()
            
            print(f"  ✓ Success: {result['secure_url']}")
            total_success += 1
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            total_failed += 1
    
    # ===== MIGRATE PRODUCT IMAGES =====
    print("\n[3/3] MIGRATING PRODUCT IMAGES")
    print("-" * 60)
    
    products = product.objects.all()
    print(f"Found {products.count()} products\n")
    
    for index, prod in enumerate(products, 1):
        print(f"[{index}/{products.count()}] Processing: {prod.name}")
        
        if not prod.product_image:
            print(f"  ⊘ No image - skipping")
            total_skipped += 1
            continue
        
        try:
            if hasattr(prod.product_image, 'path'):
                local_path = prod.product_image.path
            else:
                print(f"  ⊘ Already on cloud - skipping")
                total_skipped += 1
                continue
            
            if not os.path.exists(local_path):
                print(f"  ✗ File not found: {local_path}")
                total_failed += 1
                continue
            
            filename = os.path.basename(local_path)
            print(f"  ↑ Uploading: {filename}")
            
            result = cloudinary.uploader.upload(
                local_path,
                folder="products",
                public_id=f"product_{prod.id}_{Path(filename).stem}",
                overwrite=True,
                resource_type="auto"
            )
            
            prod.product_image = result['secure_url']
            prod.save()
            
            print(f"  ✓ Success: {result['secure_url']}")
            total_success += 1
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            total_failed += 1
    
    # ===== FINAL SUMMARY =====
    print(f"\n{'='*60}")
    print(f"MIGRATION COMPLETE")
    print(f"{'='*60}")
    print(f"✓ Successful uploads: {total_success}")
    print(f"✗ Failed uploads: {total_failed}")
    print(f"⊘ Skipped: {total_skipped}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    print("\n⚠️  CLOUDINARY IMAGE MIGRATION TOOL")
    print("=" * 60)
    print("This will upload all local images to Cloudinary:")
    print("  • Carousel images")
    print("  • Category images")
    print("  • Product images")
    print("=" * 60)
    
    # Verify Cloudinary configuration
    try:
        config = cloudinary.config()
        print(f"\n✓ Cloudinary Cloud Name: {config.cloud_name}")
        print(f"✓ API Key: {config.api_key[:4]}...{config.api_key[-4:]}")
        print(f"✓ Configuration verified!\n")
    except Exception as e:
        print(f"\n✗ ERROR: Cloudinary not configured properly!")
        print(f"Error: {str(e)}")
        print("Check your settings.py file.\n")
        exit(1)
    
    # Final confirmation
    response = input("⚠️  Continue with migration? (type 'YES' to proceed): ")
    
    if response == 'YES':
        migrate_images()
    else:
        print("\n❌ Migration cancelled.\n")