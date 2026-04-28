"""Settings para execução de testes (pytest).

Otimizado para velocidade: hash de senha barato, Langfuse desativado,
Celery em modo eager (executa tasks inline, sem broker).
"""

from .base import *  # noqa: F401, F403

DEBUG = False
LANGFUSE_ENABLED = False

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
