import os
import environ
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    CORS_ALLOW_ALL=(bool, False),
    DB_PORT=(str, "5432"),
    REDIS_URL=(str, "redis://localhost:6379"),
    CONN_MAX_AGE=(int, 60),
)

environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = env("JWT_SECRET_KEY", default="synapse-dev-secret-change-in-prod-32chars!")

DEBUG = env("DEBUG")

if SECRET_KEY == "synapse-dev-secret-change-in-prod-32chars!" and not DEBUG:
    raise RuntimeError(
        "SECRET_KEY must be changed from the insecure default when DEBUG=False. "
        "Set JWT_SECRET_KEY in your environment."
    )

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

DJANGO_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "channels",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.ngo",
    "apps.volunteer",
    "apps.chatbot",
    "apps.guest",
    "apps.graph",
    "apps.ingest",
    "apps.realtime",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "apps.core.middleware.GuestSessionMiddleware",
    "apps.core.middleware.RequestLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", default="synapseai"),
        "USER": env("DB_USER", default="postgres"),
        "PASSWORD": env("DB_PASSWORD", default="postgres"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT"),
        "CONN_MAX_AGE": env("CONN_MAX_AGE"),
        "OPTIONS": {"connect_timeout": 10},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.core.authentication.SynapseJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=24),
    "ALGORITHM": "HS256",
    "SIGNING_KEY": env("JWT_SECRET_KEY", default="synapse-dev-secret-change-in-prod-32chars!"),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "sub",
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("REDIS_URL")],
        },
    }
}

_FRONTEND_URL = env("FRONTEND_URL", default="")
_EXTRA_ORIGINS = [o.strip() for o in env("ALLOWED_ORIGINS", default="").split(",") if o.strip()]

CORS_ALLOWED_ORIGINS = list(filter(None, [
    "http://localhost:3000",
    "http://localhost:3001",
    _FRONTEND_URL,
] + _EXTRA_ORIGINS))

CORS_ALLOW_ALL_ORIGINS = False  # never allow all origins; use CORS_ALLOWED_ORIGINS above
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
CORS_ALLOW_HEADERS = [
    "Authorization",
    "Content-Type",
    "X-Request-ID",
    "X-Seed-Secret",
    "X-Service-Secret",
    "X-Metrics-Token",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# External service config (read by service modules)
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEOAPIFY_API_KEY = env("GEOAPIFY_API_KEY", default="")
NEO4J_URI = env("NEO4J_URI", default="bolt://localhost:7687")
NEO4J_USER = env("NEO4J_USER", default="neo4j")
NEO4J_PASSWORD = env("NEO4J_PASSWORD", default="")
REDIS_HOST = env("REDIS_HOST", default="localhost")
REDIS_PORT = env("REDIS_PORT", default="6379")
REDIS_DB = env("REDIS_DB", default="0")
REDIS_LOCATION_TTL_SECONDS = env.int("REDIS_LOCATION_TTL_SECONDS", default=120)
ENABLE_DYNAMIC_REASSIGNMENT = env.bool("ENABLE_DYNAMIC_REASSIGNMENT", default=True)
REASSIGNMENT_MOVE_THRESHOLD_KM = env.float("REASSIGNMENT_MOVE_THRESHOLD_KM", default=0.2)

