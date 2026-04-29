"""NinjaAPI raiz do MedChat.

Aqui ficam apenas endpoints que **não dependem de tenant** —
hoje, os health checks (`/ready` e `/health`). Endpoints de
domínio (paciente, agendamento) virão em routers separados
e exigirão `X-Clinic-Slug` resolvido pelo `RLSMiddleware`.

A divisão `/ready` × `/health` segue convenção Kubernetes
(probes):

- **`/ready`** — *readiness*: "estou pronto para receber
  tráfego?". Check rápido e barato (só Postgres). Se falhar,
  o orquestrador para de mandar requests aqui mas não
  reinicia o container.
- **`/health`** — *liveness* + dependências externas:
  "estou minimamente saudável e minhas dependências
  respondem?". Inclui Redis (cache + broker) e Celery
  workers. Se falhar, o orquestrador reinicia.

Falha em qualquer check → HTTP 503 + JSON `{"status":
"degraded", ...}` (semântica clara para LB e dashboards).
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse
from ninja import NinjaAPI

logger = logging.getLogger(__name__)

api = NinjaAPI(
    title="MedChat API",
    version="1.0.0",
    description="Backend do MedChat — secretária virtual de clínicas via WhatsApp.",
)


def _check_postgres() -> str:
    """Confirma que o banco aceita queries simples. Retorna 'ok' ou
    string com prefixo `erro:` para diagnóstico no payload."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # noqa: BLE001 — health check captura qualquer falha
        return f"erro: {exc!r}"
    return "ok"


def _check_redis() -> str:
    """Round-trip set/get no cache (Redis configurado em `base.py`)."""
    try:
        cache.set("health-check", "1", timeout=5)
        if cache.get("health-check") != "1":
            return "round_trip_falhou"
    except Exception as exc:  # noqa: BLE001
        return f"erro: {exc!r}"
    return "ok"


def _check_celery() -> str:
    """Pinga workers via Celery broadcast. `no_workers` quando o
    broker está OK mas nenhum worker respondeu no timeout — distinto
    de `erro` (broker indisponível)."""
    try:
        # Import local para deixar o módulo importável mesmo se Celery
        # estiver com algum problema de inicialização (não bloqueia
        # `/ready`, que não chama esta função).
        from config.celery import app as celery_app

        respostas = celery_app.control.ping(timeout=2)
        if not respostas:
            return "no_workers"
    except Exception as exc:  # noqa: BLE001
        return f"erro: {exc!r}"
    return "ok"


def _resposta_health(checks: dict[str, str]) -> JsonResponse:
    """Constrói a resposta com `status` agregado e código HTTP coerente."""
    saudavel = all(valor == "ok" for valor in checks.values())
    payload: dict[str, Any] = {
        "status": "ok" if saudavel else "degraded",
        "checks": checks,
    }
    return JsonResponse(payload, status=200 if saudavel else 503)


@api.get("/ready", summary="Readiness probe", tags=["health"])
def ready(request: HttpRequest) -> JsonResponse:
    """Postgres responde a `SELECT 1` → pronto pra tráfego."""
    checks = {"postgres": _check_postgres()}
    return _resposta_health(checks)


@api.get("/health", summary="Liveness probe + dependências", tags=["health"])
def health(request: HttpRequest) -> JsonResponse:
    """Postgres + Redis + Celery (workers respondendo a ping)."""
    checks = {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
        "celery": _check_celery(),
    }
    return _resposta_health(checks)
