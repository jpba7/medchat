"""Testes de integração da camada de multi-tenancy via RLS.

Validam que a infraestrutura SQL (roles, funções helper) e os
helpers Python (`tenant_session`, `@with_tenant`) se comportam como
contratado. Roda contra Postgres real — não há mock de banco.
"""

from __future__ import annotations

import pytest
from django.db import connection

from apps.clinics.models import Clinica
from apps.core.tenancy import with_tenant


def test_clinica_e_global(clinica_a, clinica_b):
    """Clinica é tabela GLOBAL: criável e listável sem `app.clinica_id`.

    Garante que a raiz de tenancy não ficou submetida a RLS por
    engano — caso contrário, o `RLSMiddleware` não conseguiria
    resolver o tenant a partir do header `X-Clinic-Slug`.
    """
    slugs = set(Clinica.objects.values_list("slug", flat=True))
    assert {"clinica-a", "clinica-b"}.issubset(slugs)


def test_funcao_apply_rls_policy_existe(db):
    """`apply_rls_policy(regclass) -> void` foi criada pela 0001_rls_setup."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT pg_get_function_result(p.oid),
                   pg_get_function_arguments(p.oid)
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE p.proname = 'apply_rls_policy'
              AND n.nspname = 'public'
            """
        )
        row = cursor.fetchone()

    assert row is not None, "função apply_rls_policy não existe"
    result_type, args = row
    assert result_type == "void"
    assert "regclass" in args


def test_funcao_drop_rls_policy_existe(db):
    """`drop_rls_policy(regclass) -> void` foi criada pela 0001_rls_setup."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT pg_get_function_result(p.oid),
                   pg_get_function_arguments(p.oid)
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE p.proname = 'drop_rls_policy'
              AND n.nspname = 'public'
            """
        )
        row = cursor.fetchone()

    assert row is not None, "função drop_rls_policy não existe"
    result_type, args = row
    assert result_type == "void"
    assert "regclass" in args


def test_role_app_readwrite_existe_sem_bypass(db):
    """`app_readwrite` existe e NÃO tem BYPASSRLS (defesa em profundidade)."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolbypassrls FROM pg_roles WHERE rolname = 'app_readwrite'"
        )
        row = cursor.fetchone()

    assert row is not None, "role app_readwrite não existe"
    assert row[0] is False, "app_readwrite não pode ter BYPASSRLS"


def test_role_app_jobs_existe_com_bypass(db):
    """`app_jobs` existe e TEM BYPASSRLS (jobs cross-tenant)."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolbypassrls FROM pg_roles WHERE rolname = 'app_jobs'"
        )
        row = cursor.fetchone()

    assert row is not None, "role app_jobs não existe"
    assert row[0] is True, "app_jobs precisa de BYPASSRLS para tasks cross-tenant"


@pytest.mark.django_db(transaction=True)
def test_tenant_session_seta_e_descarta_app_clinica_id(tenant_a):
    """Dentro de `tenant_session`, `app.clinica_id` está setado.

    Após sair, o `SET LOCAL` é descartado junto com a transação —
    nova consulta retorna string vazia (com o flag `missing_ok=true`
    do `current_setting`).

    Usa `transaction=True` porque `tenant_session` abre sua própria
    `transaction.atomic()` — incompatível com a transação de teste
    da fixture `db` padrão.
    """
    with tenant_a() as clinica:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.clinica_id', true)")
            valor_dentro = cursor.fetchone()[0]
        assert valor_dentro == str(clinica.id)

    # Fora do `with`: a transação já comitou e o SET LOCAL expirou.
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.clinica_id', true)")
        valor_fora = cursor.fetchone()[0]
    assert not valor_fora, (
        f"`app.clinica_id` deveria ter sido descartado, mas ficou: {valor_fora!r}"
    )


def test_with_tenant_decorator_exige_kwarg(db):
    """Sem `clinica_id` kwarg, `@with_tenant` levanta RuntimeError."""

    @with_tenant
    def tarefa_dummy(**kwargs):
        return "ok"

    with pytest.raises(RuntimeError, match="kwarg"):
        tarefa_dummy()


@pytest.mark.django_db(transaction=True)
def test_with_tenant_decorator_executa_dentro_da_sessao(clinica_a):
    """Com `clinica_id` kwarg, o corpo roda com `app.clinica_id` setado.

    `transaction=True` porque `@with_tenant` chama `tenant_session`,
    que abre `transaction.atomic()` próprio.
    """
    valores_capturados = {}

    @with_tenant
    def tarefa_dummy(*, clinica_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.clinica_id', true)")
            valores_capturados["app_clinica_id"] = cursor.fetchone()[0]
        return clinica_id

    retorno = tarefa_dummy(clinica_id=clinica_a.id)

    assert retorno == clinica_a.id
    assert valores_capturados["app_clinica_id"] == str(clinica_a.id)
