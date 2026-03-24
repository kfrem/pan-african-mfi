"""
Test-specific Django settings.
Uses SQLite in-memory for fast, isolated unit tests.
"""
from config.settings import *  # noqa: F401, F403

# Override database to SQLite for test isolation and speed
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations for speed — let Django build tables from models directly
class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Silence logging during tests
import logging
logging.disable(logging.CRITICAL)

# Use a fast password hasher
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Disable Celery task execution during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable external services
AFRICAS_TALKING_API_KEY = 'test'
AFRICAS_TALKING_USERNAME = 'sandbox'
RESEND_API_KEY = 'test'
SUPABASE_URL = 'http://localhost:54321'
SUPABASE_ANON_KEY = 'test-anon-key'
SUPABASE_SERVICE_ROLE_KEY = 'test-service-key'

# Disable SSL redirect in tests
SECURE_SSL_REDIRECT = False

# Override DRF auth to avoid JWT/cryptography imports in tests
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'rest_framework.authentication.SessionAuthentication',
]

# Remove custom middleware that requires live Supabase
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
