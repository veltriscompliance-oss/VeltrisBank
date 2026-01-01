"""
Django settings for Veltris project.
TRULY COMPLETE & ACCURATE PRODUCTION VERSION
"""

from pathlib import Path
import os
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- SECURITY ---
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-veltris-prod-key-fixed-9921')

# Automatically sets DEBUG to False when live on Railway
DEBUG = 'RAILWAY_ENVIRONMENT' not in os.environ

ALLOWED_HOSTS = ['*', 'veltris.online', 'www.veltris.online', '.railway.app']

# Trust your custom domain for secure form submissions (Login/Transfers)
CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://*.up.railway.app',
    'https://veltris.online',
    'https://www.veltris.online',
    'https://veltrishq.online',
    'https://www.veltrishq.online'
]

# --- APPLICATION DEFINITION ---
INSTALLED_APPS = [
    'jazzmin',  # Professional Admin UI
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',
    'django.contrib.humanize',
    'anymail',  # Professional Email API
    'account',  # Your core banking app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # --- CUSTOM SECURITY MIDDLEWARE (BOT PROTECTION) ---
    'core.middleware.SecurityHeadersMiddleware',
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

# --- DATABASE (PERMANENT POSTGRES) ---
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3'),
        conn_max_age=600
    )
}

# --- AUTHENTICATION & SESSIONS ---
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

SESSION_COOKIE_AGE = 1209600 # 2 weeks
SESSION_SAVE_EVERY_REQUEST = True
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- INTERNATIONALIZATION ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- STATIC & MEDIA FILES ---
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

WHITENOISE_MANIFEST_STRICT = False

MEDIA_URL = '/media/'
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}
# --- EMAIL CONFIGURATION (SMART SWITCH) ---
DEFAULT_FROM_EMAIL = "support@veltris.online"
EMAIL_HOST_USER = DEFAULT_FROM_EMAIL

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    ANYMAIL = {} 
else:
    EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
    ANYMAIL = {
        "BREVO_API_KEY": os.environ.get("BREVO_API_KEY", ""), 
}
# --- AI CONFIGURATION (GEMINI) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# --- JAZZMIN ADMIN DESIGN ---
JAZZMIN_SETTINGS = {
    "site_title": "Veltris Admin",
    "site_header": "Veltris HQ",
    "site_brand": "Veltris Operations",
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

JAZZMIN_UI_TWEAKS = {
    "theme": "darkly",
}