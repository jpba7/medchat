"""Pacote de configuração do MedChat.

Exporta `celery_app` para que `celery -A config worker` consiga
descobrir o objeto Celery sem importação extra. Também garante
que o Celery seja inicializado quando Django carrega — necessário
para que `@shared_task` consiga registrar tasks no app correto.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
