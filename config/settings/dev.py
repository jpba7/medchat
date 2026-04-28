"""Settings de desenvolvimento local.

Carregado por padrão via `manage.py`, `wsgi.py` e `asgi.py`.
"""

from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
