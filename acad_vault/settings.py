"""
Django settings for acad_vault (MUDRA) project.
"""

from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY
# ─────────────────────────────────────────────────────────────────────────────

# IMPORTANT: Change this in production and store in an environment variable!
SECRET_KEY = 'django-insecure-ohh4*(lb_mq6$cnmhg@*#c!7t)a5^u@a0ww)(3&%v9gx0($$q*'

DEBUG = True  # Set to False in production

# ──────────────────────────────────────────────────────────────────────────────
# ALLOWED HOSTS
#
# 'localhost' and '127.0.0.1' are the two origins that browsers treat as a
# "Secure Context", meaning navigator.mediaDevices.getUserMedia() (camera) and
# the QR scanner will WORK without HTTPS.
#
# NEVER access the dev server via your machine's LAN IP (192.168.x.x) if you
# want camera features — that's an insecure context and browsers will block it.
# ──────────────────────────────────────────────────────────────────────────────
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
]


# ─────────────────────────────────────────────────────────────────────────────
# INSTALLED APPS
# ─────────────────────────────────────────────────────────────────────────────

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]


# ─────────────────────────────────────────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────────────────────────────────────────

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'acad_vault.urls'


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────

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
            ],
        },
    },
]

WSGI_APPLICATION = 'acad_vault.wsgi.application'


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE — SQLite (production: swap for PostgreSQL)
# ─────────────────────────────────────────────────────────────────────────────

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ─────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION
# ─────────────────────────────────────────────────────────────────────────────

AUTH_USER_MODEL       = 'core.BankUser'
LOGIN_URL             = 'login'
LOGIN_REDIRECT_URL    = 'dashboard'
LOGOUT_REDIRECT_URL   = 'home'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ─────────────────────────────────────────────────────────────────────────────
# SESSION & CSRF COOKIES
#
# SameSite=Lax ensures cookies are sent on same-origin AJAX requests (fetch)
# but NOT on cross-site requests (CSRF protection).
# ─────────────────────────────────────────────────────────────────────────────

SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE    = 'Lax'
SESSION_COOKIE_SECURE   = False   # Set True in production (requires HTTPS)
CSRF_COOKIE_SECURE      = False   # Set True in production (requires HTTPS)

# Production HTTPS proxy header (uncomment when deploying behind nginx/gunicorn):
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# ─────────────────────────────────────────────────────────────────────────────
# INTERNATIONALIZATION
# ─────────────────────────────────────────────────────────────────────────────

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'   # IST for correct timestamps
USE_I18N      = True
USE_TZ        = True


# ─────────────────────────────────────────────────────────────────────────────
# STATIC FILES
# ─────────────────────────────────────────────────────────────────────────────

STATIC_URL = 'static/'

# ─────────────────────────────────────────────────────────────────────────────
# MESSAGE STORAGE (uses session for flash messages)
# ─────────────────────────────────────────────────────────────────────────────

from django.contrib.messages import constants as messages_constants
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
