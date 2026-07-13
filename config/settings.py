import os
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, True),
    MEMBERSHIP_FEE=(float, 5000.00),
)
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env("DJANGO_DEBUG")
SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "unsafe-dev-secret-key"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG=False.")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME", default="")
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
if ".onrender.com" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(".onrender.com")

PRODUCTION_HOSTS = [
    "wbliquorsocity.com",
    "www.wbliquorsocity.com",
    "login.wbliquorsocity.com",
]
for host in PRODUCTION_HOSTS:
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:8000"])
if RENDER_EXTERNAL_HOSTNAME:
    render_origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)
if "https://*.onrender.com" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append("https://*.onrender.com")
if "https://*.wbliquorsocity.com" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append("https://*.wbliquorsocity.com")
for host in PRODUCTION_HOSTS:
    origin = f"https://{host}"
    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "cloudinary",
    "cloudinary_storage",
    "storages",
    "accounts",
    "membership",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "membership.context_processors.association_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

default_sqlite_path = BASE_DIR / "db.sqlite3"
if "OneDrive" in BASE_DIR.parts and os.environ.get("LOCALAPPDATA"):
    default_sqlite_path = Path(os.environ["LOCALAPPDATA"]) / "Registration" / "db.sqlite3"
    default_sqlite_path.parent.mkdir(parents=True, exist_ok=True)

DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{default_sqlite_path.as_posix()}")}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailOrMobileBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

USE_CLOUDINARY = env.bool("USE_CLOUDINARY", default=False)
USE_R2 = env.bool("USE_R2", default=False)

if USE_CLOUDINARY:
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": env("CLOUDINARY_CLOUD_NAME", default=""),
        "API_KEY": env("CLOUDINARY_API_KEY", default=""),
        "API_SECRET": env("CLOUDINARY_API_SECRET", default=""),
        "SECURE": True,
    }
    STORAGES = {
        "default": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
elif USE_R2:
    # Cloudflare R2 (S3-compatible): 10GB free, no egress fees, serves PDFs
    # inline with correct content-type. Set in .env:
    #   USE_R2=True
    #   R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET
    #   R2_PUBLIC_URL (custom domain or the r2.dev URL)
    AWS_ACCESS_KEY_ID = env("R2_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("R2_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = env("R2_BUCKET", default="")
    AWS_S3_ENDPOINT_URL = f"https://{env('R2_ACCOUNT_ID', default='')}.r2.cloudflarestorage.com"
    AWS_S3_CUSTOM_DOMAIN = env("R2_PUBLIC_URL", default="")
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = "public-read"
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_ADDRESSING_STYLE = "path"
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ----------------------------------------------------------------------
# Logging configuration
# ----------------------------------------------------------------------
import os

LOG_DIR = BASE_DIR / "logs"
if not LOG_DIR.exists():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[%(asctime)s] %(levelname)s %(name)s %(message)s"},
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": LOG_DIR / "app.log",
            "formatter": "verbose",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "": {"handlers": ["file", "console"], "level": "INFO"},
        "django": {"handlers": ["file", "console"], "level": "INFO", "propagate": True},
    },
}

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "member_dashboard"
LOGOUT_REDIRECT_URL = "https://wbliquorsocity.com/"

ASSOCIATION_NAME = env("ASSOCIATION_NAME", default="WB Foreign Liquor and IML Licensees")
MEMBERSHIP_FEE = env("MEMBERSHIP_FEE")
PAYMENT_UPI_ID = env("PAYMENT_UPI_ID", default="")
PAYMENT_BANK_NAME = env("PAYMENT_BANK_NAME", default="")
PAYMENT_ACCOUNT_NAME = env("PAYMENT_ACCOUNT_NAME", default="")
PAYMENT_ACCOUNT_NUMBER = env("PAYMENT_ACCOUNT_NUMBER", default="")
PAYMENT_IFSC = env("PAYMENT_IFSC", default="")
SITE_URL = env(
    "SITE_URL",
    default=f"https://{RENDER_EXTERNAL_HOSTNAME}" if RENDER_EXTERNAL_HOSTNAME else "http://localhost:8000",
).rstrip("/")

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default=env("SMTP_HOST", default="smtp.gmail.com"))
EMAIL_PORT = env.int("EMAIL_PORT", default=env.int("SMTP_PORT", default=587))
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=env.bool("SMTP_USE_SSL", default=EMAIL_PORT == 465))
if EMAIL_PORT == 465:
    EMAIL_USE_SSL = True
EMAIL_USE_TLS = False if EMAIL_USE_SSL else env.bool("EMAIL_USE_TLS", default=env.bool("SMTP_USE_TLS", default=True))
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default=env("SMTP_USERNAME", default=""))
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default=env("SMTP_PASSWORD", default=""))
SMTP_FROM_EMAIL = env("SMTP_FROM_EMAIL", default="")
SMTP_FROM_NAME = env("SMTP_FROM_NAME", default="")
SMTP_DEFAULT_FROM_EMAIL = (
    f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>" if SMTP_FROM_EMAIL and SMTP_FROM_NAME else SMTP_FROM_EMAIL
)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default=SMTP_DEFAULT_FROM_EMAIL or EMAIL_HOST_USER or "noreply@example.com",
)
SMTP_ADMIN_RECIPIENTS = env.list("SMTP_ADMIN_RECIPIENTS", default=[])
ADMIN_NOTIFICATION_EMAIL = env("ADMIN_NOTIFICATION_EMAIL", default="societywelfarewbfllicences@gmail.com")

OTP_EXPIRY_MINUTES = env.int("OTP_EXPIRY_MINUTES", default=10)
OTP_LENGTH = env.int("OTP_LENGTH", default=6)
ACCOUNT_REQUIRE_OTP_VERIFICATION = env.bool("ACCOUNT_REQUIRE_OTP_VERIFICATION", default=False)
PINBOT_API_BASE_URL = env("PINBOT_API_BASE_URL", default="https://partnersv1.pinbot.ai/v3")
PINBOT_PHONE_NUMBER_ID = env("PINBOT_PHONE_NUMBER_ID", default="")
PINBOT_API_KEY = env("PINBOT_API_KEY", default="")
PINBOT_LANGUAGE_CODE = env("PINBOT_LANGUAGE_CODE", default="en")
PINBOT_TIMEOUT_SECONDS = env.int("PINBOT_TIMEOUT_SECONDS", default=10)
PINBOT_NOTIFICATION_TEMPLATE_NAME = env("PINBOT_NOTIFICATION_TEMPLATE_NAME", default="support_request")
WHATSAPP_NOTIFICATIONS_ENABLED = env.bool("WHATSAPP_NOTIFICATIONS_ENABLED", default=False)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_NAME = env("SESSION_COOKIE_NAME", default="wbliquor_sessionid")
CSRF_COOKIE_NAME = env("CSRF_COOKIE_NAME", default="wbliquor_csrftoken")
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)
SESSION_COOKIE_DOMAIN = env("SESSION_COOKIE_DOMAIN", default=None if DEBUG else ".wbliquorsocity.com") or None
CSRF_COOKIE_DOMAIN = env("CSRF_COOKIE_DOMAIN", default=SESSION_COOKIE_DOMAIN) or SESSION_COOKIE_DOMAIN
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", default="Lax")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=not DEBUG)
X_FRAME_OPTIONS = "DENY"
