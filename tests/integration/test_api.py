"""Testes dos endpoints `/api/ready` e `/api/health` (Ninja).

Os checks individuais (`_check_postgres`, `_check_redis`,
`_check_celery`) são funções puras em `config/api.py` — fácil
de mockar via `monkeypatch` nos cenários `degraded`.

A rota `/api/health*` está em `PUBLIC_PATH_PREFIXES` do
`RLSMiddleware`, então não precisa de header `X-Clinic-Slug`.
"""

from __future__ import annotations

import pytest

from config import api as api_module


@pytest.mark.django_db
def test_ready_ok(client):
    """Postgres respondendo → 200 + `status: ok`."""
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"postgres": "ok"}}


@pytest.mark.django_db
def test_health_ok_com_todas_dependencias(client, monkeypatch):
    """Mocka `_check_celery` para retornar `ok` (em modo eager o
    `control.ping` é instável). Os demais checks são reais contra
    Postgres/Redis do compose."""
    monkeypatch.setattr(api_module, "_check_celery", lambda: "ok")

    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"postgres": "ok", "redis": "ok", "celery": "ok"}


@pytest.mark.django_db
def test_health_degraded_quando_celery_sem_workers(client, monkeypatch):
    """`no_workers` é distinto de `erro` — broker OK mas ninguém
    respondeu o ping. Resultado: `degraded` + HTTP 503."""
    monkeypatch.setattr(api_module, "_check_celery", lambda: "no_workers")

    response = client.get("/api/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["celery"] == "no_workers"
    # Os outros checks reais continuam OK — só Celery degradou.
    assert body["checks"]["postgres"] == "ok"


@pytest.mark.django_db
def test_health_degraded_quando_redis_falha(client, monkeypatch):
    """Resposta agregada deve refletir QUALQUER check falho
    (não só o primeiro/último)."""
    monkeypatch.setattr(
        api_module, "_check_redis", lambda: "erro: ConnectionError(...)"
    )
    monkeypatch.setattr(api_module, "_check_celery", lambda: "ok")

    response = client.get("/api/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["redis"].startswith("erro:")


@pytest.mark.django_db
def test_health_e_publico_nao_exige_header_clinic_slug(client):
    """Garantia explícita: `RLSMiddleware` libera `/api/health` sem
    header. Se essa rota saísse de `PUBLIC_PATH_PREFIXES` por
    engano, o middleware retornaria 500 antes da view rodar."""
    response = client.get("/api/health")
    # Não 500 (que seria `tenant_nao_resolvido`).
    assert response.status_code in (200, 503)
