"""Pengaturan Lafex. Semua yang berbeda antar lingkungan dibaca dari variabel lingkungan."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
	return os.environ.get(name, default)


def env_bool(name, default=False):
	return str(env(name, str(default))).lower() in ('1', 'true', 'yes', 'on')


DEBUG = env_bool('DEBUG', False)
SECRET_KEY = env('SECRET_KEY', 'dev-only-insecure-key' if DEBUG else None)
if not SECRET_KEY:
	raise RuntimeError('SECRET_KEY wajib diatur saat DEBUG mati.')
ALLOWED_HOSTS = [h for h in env('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h]
CSRF_TRUSTED_ORIGINS = [o for o in env('CSRF_TRUSTED_ORIGINS', '').split(',') if o]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'config',
    'users',
    'billing',
    'curriculum',
    'tutor',
    'report',
    'main',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'lafex.urls'
WSGI_APPLICATION = 'lafex.wsgi.application'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
        'main.context_processors.strings',
    ]},
}]

# Database: MySQL untuk produksi (DB_ENGINE=mysql); SQLite untuk pengembangan cepat.
if env('DB_ENGINE', 'sqlite') == 'mysql':
	DATABASES = {'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME', 'lafex'),
        'USER': env('DB_USER', 'lafex'),
        'PASSWORD': env('DB_PASSWORD', ''),
        'HOST': env('DB_HOST', '127.0.0.1'),
        'PORT': env('DB_PORT', '3306'),
        # utf8mb4 wajib: Tetun, Korea, Jepang, dan emoji harus tersimpan benar.
        'OPTIONS': {'charset': 'utf8mb4', 'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"},
        'CONN_MAX_AGE': 60,
        'TEST': {'CHARSET': 'utf8mb4', 'COLLATION': 'utf8mb4_unicode_ci'},
    }}
else:
	DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_USER_MODEL = 'users.User'
LOGIN_URL = '/login/'
LANGUAGE_CODE = 'en'
TIME_ZONE = 'Asia/Dili'
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'
                    if not DEBUG else 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

# Sesi panjang: pengguna masuk sekali per perangkat (tanpa PIN).
SESSION_COOKIE_AGE = 60 * 60 * 24 * 180
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
if not DEBUG:
	SESSION_COOKIE_SECURE = True
	CSRF_COOKIE_SECURE = True
	SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
	SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
	SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30

# Email kode masuk: konsol saat pengembangan, SMTP di produksi.
if env('EMAIL_HOST'):
	EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
	EMAIL_HOST = env('EMAIL_HOST')
	EMAIL_PORT = int(env('EMAIL_PORT', '587'))
	EMAIL_HOST_USER = env('EMAIL_HOST_USER', '')
	EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', '')
	EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
else:
	EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', 'Lafex <no-reply@lafex.local>')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['config.auth.SessionAuth401'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],  # tanpa browsable API
    'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
    'EXCEPTION_HANDLER': 'config.api.exception_handler',
}

# ---- Lafex ----
LOGIN_CODE_TTL_MINUTES = 10
LOGIN_CODE_MAX_ATTEMPTS = 5
LOGIN_CODES_PER_HOUR = 5

FREE_TURNS_PER_DAY = int(env('FREE_TURNS_PER_DAY', '5'))
PAID_TURNS_PER_DAY = int(env('PAID_TURNS_PER_DAY', '150'))

# Model default claude-opus-5-5; ganti dengan TUTOR_MODEL (mis. claude-haiku-5-5) untuk menekan biaya.
TUTOR_MODEL = env('TUTOR_MODEL', 'claude-opus-5-5')
LAFEX_OFFLINE = env_bool('LAFEX_OFFLINE', False)  # paksa tutor skrip tanpa AI (demo/tes)
ASSET_VERSION = env('ASSET_VERSION', '1')         # naikkan untuk memperbarui cache PWA

LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
