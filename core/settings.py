"""
Django settings for Veltris Bank project.
Finalized Production Version for veltris.online
"""

from pathlib import Path
import os
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- SECURITY ---
# In production, this should ideally be an environment variable
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-veltris-bank-production-key-9928341')

# Debug is FALSE in production (when running on Railway)
DEBUG = 'RAILWAY_ENVIRONMENT' not in os.environ

# Domain settings
ALLOWED_HOSTS = ['*', 'veltris.online', 'www.veltris.online']

# Crucial for Login and Transfers to work on your custom domain
CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://*.up.railway.app',
    'https://veltris.online',
    'https://www.veltris.online'
]

# --- APPLICATIONS ---
INSTALLED_APPS = [
    'jazzmin', # Admin theme must be first
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'account',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Essential for static files on Railway
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

# --- DATABASE (PostgreSQL for Railway) ---
# This looks for DATABASE_URL in environment variables. 
# If not found (locally), it falls back to SQLite.
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3'),
        conn_max_age=600
    )
}

# --- STATIC & MEDIA ---
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- HOSTINGER EMAIL SETUP ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.hostinger.com'
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False
EMAIL_HOST_USER = 'support@veltris.online'
# IMPORTANT: Put your Hostinger email password inside the quotes below
EMAIL_HOST_PASSWORD = '123kenUbong$' 

# --- SESSION & SECURITY SETTINGS ---
SESSION_COOKIE_AGE = 1209600 # 2 weeks
SESSION_SAVE_EVERY_REQUEST = True
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- JAZZMIN ADMIN DESIGN ---
JAZZMIN_SETTINGS = {
    "site_title": "Veltris Admin",
    "site_header": "Veltris Operations",
    "site_brand": "Veltris HQ",
    "welcome_sign": "Authorized Access Only",
    "copyright": "Veltris Technologies Inc",
    "search_model": "auth.User",
    "show_sidebar": True,
    "navigation_expanded": True,
    "theme": "darkly",
    "icons": {
        "auth": "fas fa-users-cog",
        "account.Account": "fas fa-university",
        "account.Transaction": "fas fa-exchange-alt",
        "account.Loan": "fas fa-hand-holding-usd",
    },
}