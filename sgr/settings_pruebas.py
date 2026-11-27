"""Local/test settings: explicitly SQLite, never RDS. No private environment files."""
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "local-only-sgr-academic-tests-not-production"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
INSTALLED_APPS = ["django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "organizacion", "actividades", "agenda", "resultados"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware", "sgr.middleware.LoginRequiredMiddleware", "sgr.middleware.CambioClaveObligatorioMiddleware"]
ROOT_URLCONF = "sgr.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True, "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGIN_EXEMPT_URLS = ["/login/", "/logout/", "/admin/", "/static/", "/cuenta/recuperar/"]
AUTHENTICATION_BACKENDS = ["sgr.backends.ClaveTemporalBackend"]
# V4.2 (local): los correos se muestran en la consola; el ejecutor de pruebas usa locmem automáticamente.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "SGR local <no-responder@localhost>"
SGR_CLAVE_TEMPORAL_HORAS = 72
PASSWORD_RESET_TIMEOUT = 3600
SGR_RECUPERACION_LIMITE = 5
SGR_RECUPERACION_VENTANA = 3600
SGR_URL_PUBLICA = ""
SGR_PROXY_IP_HEADER = ""
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "sgr-pruebas"}}
