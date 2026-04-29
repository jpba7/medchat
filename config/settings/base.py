"""Configurações base do MedChat.

Compartilhadas entre dev/test/prod. Variáveis sensíveis vêm do ambiente
via `django-environ` (lê `.env` na raiz do projeto se existir).
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    LANGFUSE_ENABLED=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

# --- Núcleo Django -----------------------------------------------------------

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-dev-only-do-not-use-in-prod",
)
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # `django.contrib.postgres` habilita ExclusionConstraint, RangeFields,
    # SearchVector, etc. Necessário para o anti-overlap de Agendamento
    # via `EXCLUDE USING GIST + tstzrange`.
    "django.contrib.postgres",
    # Terceiros
    "django_celery_beat",
    "pgtrigger",
    # Apps internos do MedChat
    "apps.core",
    "apps.clinics",
    "apps.patients",
    "apps.catalog",
    "apps.appointments",
    "apps.conversations",
    "apps.bot",
    "apps.channels",
    "apps.observability",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # `RLSMiddleware` resolve o tenant a partir do header `X-Clinic-Slug`
    # (painel) ou do canal de webhook (futuro). Roda DEPOIS de auth
    # porque tabelas auth_* não são tenant-owned, e ANTES da view
    # porque toda query de domínio depende de `app.clinica_id` setado.
    "apps.core.middleware.RLSMiddleware",
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

# --- Banco de dados ----------------------------------------------------------
# Postgres é obrigatório — RLS (Row-Level Security) é fundação multi-tenant.
# ATOMIC_REQUESTS fica False: o RLSMiddleware abre `transaction.atomic()`
# explicitamente para conseguir rodar `SET LOCAL app.clinica_id` no escopo
# correto. CONN_MAX_AGE=0 (conexão por request) é deliberado na Fase 1 para
# evitar reuso acidental de conexão com `app.clinica_id` herdado de request
# anterior. Quando tivermos pool dedicado e RESET disciplinado, podemos subir.

DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        default="postgres://medchat:medchat@localhost:5432/medchat",
    ),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = False
DATABASES["default"]["CONN_MAX_AGE"] = 0

# --- Cache + Celery ----------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
    },
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TIMEZONE = "America/Sao_Paulo"

# --- Auth padrão -------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n / tz — produto Brasil-first ---------------------------------------

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# --- Estáticos ---------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Integrações MedChat -----------------------------------------------------

ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
OPENROUTER_API_KEY = env("OPENROUTER_API_KEY", default="")

LANGFUSE_ENABLED = env("LANGFUSE_ENABLED")
LANGFUSE_HOST = env("LANGFUSE_HOST", default="http://localhost:3000")
LANGFUSE_PUBLIC_KEY = env("LANGFUSE_PUBLIC_KEY", default="")
LANGFUSE_SECRET_KEY = env("LANGFUSE_SECRET_KEY", default="")

EVOLUTION_BASE_URL = env("EVOLUTION_BASE_URL", default="")
EVOLUTION_API_KEY = env("EVOLUTION_API_KEY", default="")

# Chave Fernet para criptografar credenciais por canal (`clinica_canais.config`).
FERNET_KEY = env("FERNET_KEY", default="")
