"""
Django settings for core project.
COMPLETE & PRODUCTION READY
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- SECURITY CONFIGURATION ---
# Keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-production-key-veltris-bank-secure-8829')

# AUTO-DETECT ENVIRONMENT
# If running on Railway, 'RAILWAY_ENVIRONMENT' exists, so DEBUG becomes False.
# If running locally, it doesn't exist, so DEBUG is True.
DEBUG = 'RAILWAY_ENVIRONMENT' not in os.environ

ALLOWED_HOSTS = ['*']

# Trusted Origins for Banking Security (HTTPS)
CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app', 
    'https://*.up.railway.app',
    'http://127.0.0.1', 
    'http://localhost'
]

# --- APPLICATIONS ---
INSTALLED_APPS = [
    # 1. JAZZMIN (Admin Theme - Must be top)
    'jazzmin',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 2. UTILS
    'django.contrib.humanize',
    
    # 3. YOUR APP
    'account',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise: Critical for serving CSS/Images in Production
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [], # Uses app directories automatically
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Custom Processor for Notifications
                'account.context_processors.global_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# --- DATABASE CONFIGURATION ---
# robust logic: Uses PostgreSQL if available (Production), else SQLite (Local)
try:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3'),
            conn_max_age=600
        )
    }
except ImportError:
    # Fallback if libraries aren't installed yet
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# --- AUTHENTICATION ---
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- STATIC & MEDIA FILES ---
# This ensures CSS works on the live internet
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# For user uploads (Profile pics, KYC)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- EMAIL ENGINE (SMTP) ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 465             
EMAIL_USE_SSL = True         
EMAIL_USE_TLS = False        
EMAIL_HOST_USER = 'veltris.compliance@gmail.com'
# App Password (ensure this is valid)
EMAIL_HOST_PASSWORD = 'yawcyqbxjjvbtcxx'

# --- SECURITY: SESSION ---
SESSION_COOKIE_AGE = 300 # 5 Minutes Auto-Logout
SESSION_SAVE_EVERY_REQUEST = True
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- VELTRIS ADMIN PORTAL THEME (JAZZMIN) ---
JAZZMIN_SETTINGS = {
    "site_title": "Veltris Operations",
    "site_header": "Veltris Internal",
    "site_brand": "Veltris HQ",
    "welcome_sign": "Authorized Personnel Only",
    "copyright": "Veltris Technologies Inc",
    "search_model": "auth.User",
    
    # Top Menu
    "topmenu_links": [
        {"name": "Client Dashboard", "url": "home", "permissions": ["auth.view_user"]},
        {"name": "Support Inbox", "url": "admin:account_supportmessage_changelist"},
    ],

    # Menu Organization
    "order_with_respect_to": ["account", "auth"],
    
    # Professional Icons
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user-shield",
        "auth.Group": "fas fa-users",
        "account.Account": "fas fa-university",
        "account.Transaction": "fas fa-exchange-alt",
        "account.Loan": "fas fa-hand-holding-usd",
        "account.CreditCard": "fas fa-credit-card",
        "account.Notification": "fas fa-bell",
        "account.SupportMessage": "fas fa-headset",
    },
    
    "show_sidebar": True,
    "navigation_expanded": True,
    "changeform_format": "horizontal_tabs",
}

JAZZMIN_UI_TWEAKS = {
    "theme": "darkly", # Premium Dark Theme for Admin
    "dark_mode_theme": "darkly",
}