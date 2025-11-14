import os
from pathlib import Path
from decouple import config
import logging
import sys
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY
SECRET_KEY = config("SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = ['fammo.ai', 'localhost', '127.0.0.1']

# LOGGING
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}

# APPS
INSTALLED_APPS = [
    'modeltranslation',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'django.contrib.sites',  # Required by allauth

    # Allauth apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    'userapp',
    'chat',
    'core',
    'pet',
    'aihub',
    'subscription',
    'blog',
    'markdownify',
    'widget_tweaks',
    'markdownx',
    'formtools',
    'vets.apps.VetsConfig',
]

MODELTRANSLATION_FALLBACK_LANGUAGES = ('en',)

TAILWIND_APP_NAME = 'theme'
NPM_BIN_PATH = "C:/Program Files/nodejs/npm.cmd"

if DEBUG:
    INSTALLED_APPS += ['django_browser_reload']

# MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG:
    MIDDLEWARE += ['django_browser_reload.middleware.BrowserReloadMiddleware']

ROOT_URLCONF = 'famo.urls'
WSGI_APPLICATION = 'famo.wsgi.application'

# DATABASE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST_LOCAL'),
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

# AUTH
AUTH_USER_MODEL = 'userapp.CustomUser'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# TEMPLATES
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'subscription.context_processors.ai_usage_status',
                'famo.context_processors.social_links',
            ],
        },
    },
]

# LANGUAGE & TIMEZONE
LANGUAGE_CODE = 'en'
LANGUAGES = [
    ('en', 'English'),
    ('tr', 'Türkçe'),
    ('nl', 'Nederlands'),
]
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# STATIC FILES
STATIC_URL = 'fammo/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# MEDIA FILES
MEDIA_URL = '/fammo/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# MARKDOWNIFY
MARKDOWNIFY = {
    "default": {
        "WHITELIST_TAGS": [
            'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li',
            'ol', 'pre', 'strong', 'ul', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'img', 'hr', 'br', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
        ],
        "WHITELIST_ATTRS": ['href', 'src', 'alt', 'class', 'align'],
        "MARKDOWN_EXTENSIONS": [
            'markdown.extensions.fenced_code',
            'markdown.extensions.codehilite',
            'markdown.extensions.tables',
            'markdown.extensions.toc',
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists',
            'markdown.extensions.smarty',
        ],
    }
}

# Optional Markdownx config
MARKDOWNX_MEDIA_PATH = 'markdownx/'
MARKDOWNX_UPLOAD_CONTENT_TYPES = ('image/jpeg', 'image/png', 'image/gif', 'image/webp')
MARKDOWNX_UPLOAD_MAX_SIZE = 10 * 1024 * 1024  # 10MB
MARKDOWNX_MARKDOWN_EXTENSIONS = [
    'markdown.extensions.extra',
    'markdown.extensions.codehilite',
    'markdown.extensions.toc',
]

# OPENAI KEY
OPENAI_API_KEY = config("OPENAI_API_KEY")

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# EMAIL
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'fammo.ai.official@gmail.com'
EMAIL_HOST_PASSWORD = 'mjvq eetb qqux rhof'
DEFAULT_FROM_EMAIL = 'FAMO <fammo.ai.official@gmail.com>'

SITE_ID = 1 # Site ID should be different must be check

ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = 'optional'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_ADAPTER = 'userapp.adapters.CustomAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'userapp.adapters.CustomSocialAccountAdapter'

CONTACT_EMAIL = "info@fammo.ai"

NPM_BIN_PATH  = "/home/fammkoqw/nodevenv/nodeapp/20/bin/npm"
NODE_BIN_PATH = "/home/fammkoqw/nodevenv/nodeapp/20/bin/node"
