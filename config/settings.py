from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    MEMBERSHIP_FEE=(float, 5000.00),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-dev-secret-key")
DEBUG = env("DJANGO_DEBUG")
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

DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}

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

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Upload storage
# Local media is used by default for development.
# Set USE_CLOUDINARY=True and add Cloudinary env values on Render to store uploaded
# documents, images, and payment proofs in Cloudinary instead of the Render filesystem.
USE_CLOUDINARY = env.bool("USE_CLOUDINARY", default=False)
if USE_CLOUDINARY:
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": env("CLOUDINARY_CLOUD_NAME"),
        "API_KEY": env("CLOUDINARY_API_KEY"),
        "API_SECRET": env("CLOUDINARY_API_SECRET"),
        "SECURE": True,
    }
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
    STORAGES = {
        "default": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"},
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

OTP_EXPIRY_MINUTES = env.int("OTP_EXPIRY_MINUTES", default=10)
OTP_LENGTH = env.int("OTP_LENGTH", default=6)
ACCOUNT_REQUIRE_OTP_VERIFICATION = env.bool("ACCOUNT_REQUIRE_OTP_VERIFICATION", default=False)
WHATSAPP_OTP_ENABLED = env.bool("WHATSAPP_OTP_ENABLED", default=False)
WHATSAPP_OTP_API_URL = env("WHATSAPP_OTP_API_URL", default="")
WHATSAPP_OTP_TOKEN = env("WHATSAPP_OTP_TOKEN", default="")
WHATSAPP_OTP_FROM = env("WHATSAPP_OTP_FROM", default="")
WHATSAPP_API_URL = env("WHATSAPP_API_URL", default=WHATSAPP_OTP_API_URL)
WHATSAPP_API_TOKEN = env("WHATSAPP_API_TOKEN", default=WHATSAPP_OTP_TOKEN)
WHATSAPP_FROM = env("WHATSAPP_FROM", default=WHATSAPP_OTP_FROM)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
