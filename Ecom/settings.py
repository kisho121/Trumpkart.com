import os
import sys
from pathlib import Path
import dj_database_url
from decouple import config, Csv
import json
import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.contrib.messages import constants as messages


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)
    
# Detect if running with runserver (local development)
IS_RUNSERVER = 'runserver' in sys.argv

# Logging configuration - helps debug issues when DEBUG=False
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'debug.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

if DEBUG:
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
else:
    ALLOWED_HOSTS = [
        'trumpkart-shop.onrender.com',
        '127.0.0.1',
        'localhost',
        '.onrender.com',
    ]

# Security settings - only apply in actual production, not local testing
if not DEBUG and not IS_RUNSERVER:
    # Production security settings (on Render)
    CSRF_TRUSTED_ORIGINS = ['https://trumpkart-shop.onrender.com']
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'SAMEORIGIN'
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
else:
    # Development/local testing settings
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_HTTPONLY = False
    SESSION_COOKIE_HTTPONLY = False
    if not DEBUG:
        # For local testing with DEBUG=False
        CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:8000', 'http://localhost:8000']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'cloudinary',
    'cloudinary_storage',
    'Shop',
    'anymail',
    'widget_tweaks',
    'razorpay',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = 'Ecom.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "templates")],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Ecom.wsgi.application'

# ============================================
# CLOUDINARY CONFIGURATION (Production Only)
# ============================================

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': config('CLOUDINARY_API_KEY'),
    'API_SECRET': config('CLOUDINARY_API_SECRET'),
}

cloudinary.config(
    cloud_name=config('CLOUDINARY_CLOUD_NAME'),
    api_key=config('CLOUDINARY_API_KEY'),
    api_secret=config('CLOUDINARY_API_SECRET')
)

# ============================================
# STORAGES CONFIGURATION (Conditional)
# ============================================

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Database Configuration
# Use SQLite locally (with runserver), PostgreSQL in production
if IS_RUNSERVER or DEBUG:
    # Local development - always use SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Production on Render - use PostgreSQL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': config('DB_PORT'),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
# TIME_ZONE = 'UTC'
 # for India
TIME_ZONE = 'Asia/Kolkata' 
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)    
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
# MEDIA_ROOT = BASE_DIR / 'media'

MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',  # Maps 'error' to 'danger' for Bootstrap red color
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

INTERNAL_IPS = [
    '127.0.0.1',
]

SITE_ID = 1

# Django-allauth settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    },
}

LOGIN_REDIRECT_URL = "home"
LOGIN_URL = 'account_login'
ACCOUNT_LOGOUT_REDIRECT_URL = 'account_login'
SOCIALACCOUNT_LOGIN_ON_GET = True

# ACCOUNT_ADAPTER = 'Shop.adapters.MyAccountAdapter'

# settings.py

# Allow accounts to be authenticated via their email
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True

# Automatically link the social account to the local account if the email matches
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

# Skip the "signup" form if all required info is provided by Google
SOCIALACCOUNT_AUTO_SIGNUP = True

# Email settings for django-allauth
ACCOUNT_EMAIL_VERIFICATION = 'optional'
# Allow login using username OR email
ACCOUNT_LOGIN_METHODS = {'username', 'email'}

# Required fields during signup
ACCOUNT_SIGNUP_FIELDS = [
    'email*',
    'username*',
    'password1*',
    'password2*',
]
# ACCOUNT_EMAIL_REQUIRED = True
# ACCOUNT_AUTHENTICATION_METHOD = 'username_email'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Brevo Email Backend (via Anymail)
EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
ANYMAIL = {
    "BREVO_API_KEY": config("BREVO_API_KEY"),
    "IGNORE_RECIPIENT_STATUS": True,
}
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")

# Razorpay Settings
RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET')

CRON_SECRET_KEY = config('CRON_SECRET_KEY')

# ========== Google Sheets Configuration ==========

GOOGLE_SHEETS_CREDENTIALS = json.loads(
    config("GOOGLE_CREDENTIALS_JSON", "{}")
)

# Fix newline issue
if "private_key" in GOOGLE_SHEETS_CREDENTIALS:
    GOOGLE_SHEETS_CREDENTIALS["private_key"] = GOOGLE_SHEETS_CREDENTIALS["private_key"].replace("\\n", "\n")

# Automatically picks correct sheet based on DEBUG
if DEBUG:
    MASTER_SHEET_ID = config('MASTER_SHEET_ID')
    DEALER_SHEET_ID = config('DEALER_SHEET_ID')
    DELIVERY_SHEET_ID = config('DELIVERY_SHEET_ID')
else:
    MASTER_SHEET_ID = config('PROD_MASTER_SHEET_ID')
    DEALER_SHEET_ID = config('PROD_DEALER_SHEET_ID')
    DELIVERY_SHEET_ID = config('PROD_DELIVERY_SHEET_ID')