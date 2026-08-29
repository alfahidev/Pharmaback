import os
from .base import *

DEBUG = False

# Production Allowed Hosts (Ensures domain and internal container/healthcheck hosts are always valid)
_raw_allowed = os.getenv("ALLOWED_HOSTS", "").strip()
if _raw_allowed == "*":
    ALLOWED_HOSTS = ["*"]
else:
    _configured_hosts = [h.strip() for h in _raw_allowed.split(",") if h.strip()]
    _mandatory_hosts = [
        "pharmaback",
        "backend",
        "web",
        "app",
        "pharmacy.melakhtelecom.com",
        "api.pharmacy.melakhtelecom.com",
        ".melakhtelecom.com",
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
    ]
    ALLOWED_HOSTS = list(dict.fromkeys(_configured_hosts + _mandatory_hosts))


# Reverse Proxy & HTTPS Forwarding (Traefik / Nginx / Docker Swarm)
# Source: https://docs.djangoproject.com/en/6.0/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# SSL Redirect (Handled at reverse proxy edge; keep False by default to avoid internal redirect loops)
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() in ("true", "1")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Cookie Security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Disable DRF Browsable API in production (JSON only)
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

# Swagger/OpenAPI toggle in production (disabled unless explicitly requested)
ENABLE_SWAGGER = os.getenv("ENABLE_SWAGGER", "False").lower() in ("true", "1", "yes")

