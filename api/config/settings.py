import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR.parent / ".env")
except ImportError:
    pass

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-pulumi-visualizer-dev")
# Default off so production images are safe if DEBUG is omitted from the env.
DEBUG = os.environ.get("DEBUG", "false").lower() in {"1", "true", "yes"}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "accounts",
    "pulumi_state",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

PULUMI_STATE_BACKENDS = os.environ.get("PULUMI_STATE_BACKENDS", "")

# Browser origin after OIDC callback (Vite dev server or production UI).
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:5173").rstrip("/")

# OIDC / SSO. Leave OIDC_CLIENT_ID empty to disable.
# Either set OIDC_ISSUER (discovery) or the three explicit endpoint URLs.
OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "").strip()
OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "").strip()
OIDC_ISSUER = os.environ.get("OIDC_ISSUER", "").strip()
OIDC_DISCOVERY_URL = os.environ.get("OIDC_DISCOVERY_URL", "").strip()
OIDC_AUTH_ENDPOINT = os.environ.get("OIDC_AUTH_ENDPOINT", "").strip()
OIDC_TOKEN_ENDPOINT = os.environ.get("OIDC_TOKEN_ENDPOINT", "").strip()
OIDC_USERINFO_ENDPOINT = os.environ.get("OIDC_USERINFO_ENDPOINT", "").strip()
OIDC_SCOPES = os.environ.get("OIDC_SCOPES", "openid profile email").strip()
OIDC_LABEL = os.environ.get("OIDC_LABEL", "Sign in with SSO").strip() or "Sign in with SSO"
# Explicit callback registered at the IdP. Prefer the URL the browser hits
# (Vite proxy: http://127.0.0.1:5173/api/auth/oidc/callback/).
OIDC_REDIRECT_URI = os.environ.get("OIDC_REDIRECT_URI", "").strip()
# Comma-separated group names; empty = any authenticated user. Claim defaults to "groups".
OIDC_ALLOWED_GROUPS = {
    group.strip()
    for group in os.environ.get("OIDC_ALLOWED_GROUPS", "").split(",")
    if group.strip()
}
OIDC_GROUPS_CLAIM = os.environ.get("OIDC_GROUPS_CLAIM", "groups").strip() or "groups"
# When OIDC is enabled, password login stays available unless set to false.
OIDC_PASSWORD_LOGIN = os.environ.get("OIDC_PASSWORD_LOGIN", "true").lower() in {
    "1",
    "true",
    "yes",
}

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
