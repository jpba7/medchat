"""Configuração do Celery do MedChat.

Padrão Django+Celery: a `app` é criada aqui e exposta em
`config/__init__.py` para que o autodiscover encontre tasks
declaradas em `apps/<app>/tasks.py` automaticamente.

Settings de runtime (broker, result backend, beat) vêm do
`config/settings/base.py` via `app.config_from_object`. Tasks
em modo `eager` para testes (`config/settings/test.py`).
"""

from __future__ import annotations

import os

from celery import Celery

# Default `dev` para uso interativo (`celery -A config worker`); o
# container web/worker tem `DJANGO_SETTINGS_MODULE` no compose.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("medchat")

# `namespace="CELERY"` faz com que apenas variáveis prefixadas com
# `CELERY_` no settings sejam lidas — evita poluir o namespace
# Django (DATABASES, INSTALLED_APPS) com config Celery.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Procura `tasks.py` em cada app de `INSTALLED_APPS`. Nada de
# imports manuais — basta criar o módulo e usar `@shared_task`.
app.autodiscover_tasks()
