#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting build script"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Apply database migrations
echo "Applying migrations..."
python manage.py migrate

# Create superuser if needed
if [[ $CREATE_SUPERUSER ]]; then
  echo "Creating superuser..."
  python manage.py createsuperuser --no-input --email "$DJANGO_SUPERUSER_EMAIL"
fi

echo "Build script completed successfully"
