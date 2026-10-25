"""Shared configuration for the RMS modular monolith."""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]
env = environ.Env()
# Process environment wins. CI/hosting can disable local .env loading entirely.
if env.bool("DJANGO_READ_DOT_ENV_FILE", default=True):
    env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY.strip():
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must not be empty.")
PIN_PEPPER = env("DJANGO_PIN_PEPPER")
if len(PIN_PEPPER) < 32:
    raise ImproperlyConfigured("DJANGO_PIN_PEPPER must contain at least 32 characters.")

DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.core.apps.CoreConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.restaurants.apps.RestaurantsConfig",
    "apps.menu.apps.MenuConfig",
    "apps.orders.apps.OrdersConfig",
    "apps.kitchen.apps.KitchenConfig",
    "apps.billing.apps.BillingConfig",
    "apps.inventory.apps.InventoryConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.accounts.middleware.AdminCredentialRateLimitMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", default="rms_development"),
        "USER": env("DB_USER", default="rms_app"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env.int("DB_PORT", default=5432),
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": env.int("DB_CONNECT_TIMEOUT", default=5),
            "sslmode": env("DB_SSLMODE", default="prefer"),
        },
    },
}
if not DATABASES["default"]["PASSWORD"].strip():
    raise ImproperlyConfigured("DB_PASSWORD must not be empty.")

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.AccountBackend"]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 15},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["apps.accounts.permissions.IsAuthenticatedAndPinReady"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
}

CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = env.bool("DJANGO_CORS_ALLOW_CREDENTIALS", default=False)
CORS_URLS_REGEX = r"^/api/.*$"
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kathmandu"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"
# Logos are delivered through the authenticated API, never a public /media route.
MEDIA_URL = "/media/"
DATA_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "apps.accounts.views.csrf_failure"
ACCOUNTS_OWNER_SESSION_SECONDS = 3600
ACCOUNTS_STAFF_SESSION_SECONDS = 28800
# Atomic PostgreSQL budgets, shared by all workers and admin/API login paths.
ACCOUNTS_LOGIN_ACCOUNT_LIMIT = 5
ACCOUNTS_LOGIN_ACCOUNT_WINDOW_SECONDS = 900
ACCOUNTS_LOGIN_IP_LIMIT = 30
ACCOUNTS_LOGIN_IP_WINDOW_SECONDS = 60

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", default="INFO")},
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
}
