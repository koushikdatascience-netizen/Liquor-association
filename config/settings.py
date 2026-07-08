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

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:8000"])
if RENDER_EXTERNAL_HOSTNAME:
    render_origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)
if "https://*.onrender.com" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append("https://*.onrender.com")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "cloudinary",
    "cloudinary_storage",
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
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "member_dashboard"
LOGOUT_REDIRECT_URL = "home"

ASSOCIATION_NAME = env("ASSOCIATION_NAME", default="Liquor Association")
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
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=env.bool("SMTP_USE_SSL", default=False))
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=not EMAIL_USE_SSL)
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
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=not DEBUG)
X_FRAME_OPTIONS = "DENY"
