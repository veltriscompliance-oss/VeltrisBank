"""
Django settings for Veltris Bank project.
PERFECT PRODUCTION VERSION - VELTRIS.ONLINE
"""

from pathlib import Path
import os
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- SECURITY CONFIGURATION ---
# Use an environment variable for the secret key in production
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-veltris-bank-secure-8829-prod-key')

# Debug is FALSE in production (automatically detects Railway)
DEBUG = 'RAILWAY_ENVIRONMENT' not in os.environ

# Domain settings for veltris.online
ALLOWED_HOSTS = ['*', 'veltris.online', 'www.veltris.online', '.railway.app']

# Trust your custom domain for secure form submissions (Login/Transfers)
CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://*.up.railway.app',
    'https://veltris.online',
    'https://www.veltris.online'
]

# --- APPLICATIONS ---
INSTALLED_APPS = [
    'jazzmin',  # Professional Admin Theme (Must be top)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'anymail',  # Professional Email API Engine
    'account',  # Core Banking App
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Handles static files in production
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
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'account.context_processors.global_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# --- DATABASE CONFIGURATION (PERMANENT POSTGRES) ---
# Automatically uses Railway's Postgres URL; falls back to local SQLite for testing.
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3'),
        conn_max_age=600
    )
}

# --- STATIC & MEDIA FILES ---
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Compressed static files for faster loading
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- PROFESSIONAL EMAIL API (BREVO) ---
# Using the HTTP API (Port 443) bypasses the restricted SMTP ports (587/465)
EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
DEFAULT_FROM_EMAIL = "support@veltris.online"

ANYMAIL = {
    "BREVO_API_KEY": "3ZACFLr2YH1azM9f", # <--- PASTE YOUR API KEY HERE
}

# Values for views.py compatibility
EMAIL_HOST_USER = DEFAULT_FROM_EMAIL

# --- AUTHENTICATION & SESSIONS ---
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

# Extended session age (2 weeks)
SESSION_COOKIE_AGE = 1209600
SESSION_SAVE_EVERY_REQUEST = True
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- JAZZMIN ADMIN DESIGN ---
JAZZMIN_SETTINGS = {
    "site_title": "Veltris Admin",
    "site_header": "Veltris Operations",
    "site_brand": "Veltris HQ",
    "welcome_sign": "Authorized Personnel Only",
    "copyright": "Veltris Technologies Inc",
    "search_model": "auth.User",
    "show_sidebar": True,
    "navigation_expanded": True,
    "order_with_respect_to": ["account", "auth"],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user-shield",
        "account.Account": "fas fa-university",
        "account.Transaction": "fas fa-exchange-alt",
        "account.Loan": "fas fa-hand-holding-usd",
        "account.CreditCard": "fas fa-credit-card",
        "account.Notification": "fas fa-bell",
        "account.SupportMessage": "fas fa-headset",
    },
}

JAZZMIN_UI_TWEAKS = {
    "theme": "darkly",
    "dark_mode_theme": "darkly",
}