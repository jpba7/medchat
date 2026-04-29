"""Fixtures globais do pytest para o MedChat.

Reúne os helpers de tenancy e os tenants de teste (`clinica_a`,
`clinica_b`) usados pela suíte de integração. Pytest-django auto-
descobre este arquivo na raiz do projeto.
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest
from django.db import connection

from apps.clinics.models import Clinica
from apps.core.tenancy import tenant_session


@pytest.fixture
def clinica_a(db) -> Clinica:
    """Tenant de teste 'A'. Criada como linha global (sem RLS)."""
    return Clinica.objects.create(slug="clinica-a", nome="Clínica A")


@pytest.fixture
def clinica_b(db) -> Clinica:
    """Tenant de teste 'B'. Útil para checar isolamento cross-tenant."""
    return Clinica.objects.create(slug="clinica-b", nome="Clínica B")


@pytest.fixture
def set_app_clinica_id():
    """Retorna função `set(clinica_id)` que dispara `SET LOCAL app.clinica_id`.

    Pré-requisito: o teste já precisa estar dentro de uma transação
    atômica (`SET LOCAL` só vive dentro de uma transação). Útil quando
    o teste quer trocar o tenant da sessão sem abrir/fechar
    `tenant_session`.
    """

    def _set(clinica_id) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SET LOCAL app.clinica_id = %s",
                [str(clinica_id)],
            )

    return _set


@pytest.fixture
def tenant_a(db, clinica_a):
    """Helper para entrar na sessão Postgres da `clinica_a`.

    Uso:
        with tenant_a():
            # dentro do bloco, `app.clinica_id` está setado em A
            ...
    """

    @contextmanager
    def _enter():
        with tenant_session(clinica_a.id):
            yield clinica_a

    return _enter


@pytest.fixture
def tenant_b(db, clinica_b):
    """Helper análogo a `tenant_a`, mas para a `clinica_b`."""

    @contextmanager
    def _enter():
        with tenant_session(clinica_b.id):
            yield clinica_b

    return _enter
