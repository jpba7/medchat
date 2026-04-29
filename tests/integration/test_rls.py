"""Testes de integração da camada de multi-tenancy via RLS.

Validam que a infraestrutura SQL (roles, funções helper) e os
helpers Python (`tenant_session`, `@with_tenant`) se comportam como
contratado. Roda contra Postgres real — não há mock de banco.

Inclui também a bateria de **isolation cross-tenant**: para cada
uma das 8 tabelas tenant-aware da Onda 1, dois testes:

- `test_isolation_<modelo>` — linha criada na clínica A não
  aparece em queries da clínica B. Roda dentro de `SET LOCAL
  ROLE app_readwrite` para que a policy RLS de fato seja avaliada
  (o owner `medchat` do compose é SUPERUSER + BYPASSRLS — em
  produção, Django conecta como `app_readwrite`).
- `test_<modelo>_save_rejeita_clinica_id_diferente_da_sessao` —
  tentativa de inserir com `clinica_id` ≠ `app.clinica_id` da
  sessão dispara `ValidationError` (defesa em profundidade no
  `TenantAwareModel.save()`, independente da role).
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import time

import pytest
from django.core.exceptions import ValidationError
from django.db import connection

from apps.catalog.models import (
    Convenio,
    Especialidade,
    Medico,
    MedicoConvenio,
    MedicoDisponibilidade,
)
from apps.clinics.models import Clinica, ClinicaCanal, ClinicaPolitica
from apps.core.tenancy import tenant_session, with_tenant
from apps.patients.models import Paciente


@contextmanager
def _sessao_app_readwrite(clinica_id):
    """Combina `tenant_session` + `SET LOCAL ROLE app_readwrite`.

    Necessário nos testes de isolation porque o user `medchat` do
    docker-compose é SUPERUSER + BYPASSRLS — sem trocar a role,
    o `USING` da policy é ignorado e a query enxerga tudo. Em
    produção a aplicação conecta como `app_readwrite`, então
    estes testes refletem o comportamento real de runtime.

    Ao sair do `with`, o `SET LOCAL ROLE` (e o `SET LOCAL
    app.clinica_id`) expiram com a transação aberta pelo
    `tenant_session`.
    """
    with tenant_session(clinica_id):
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE app_readwrite")
        yield


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
        cursor.execute("SELECT rolbypassrls FROM pg_roles WHERE rolname = 'app_jobs'")
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


# ---------------------------------------------------------------------------
# Isolation cross-tenant — uma linha criada na clínica A não aparece para B.
# Cada teste cria a mínima cadeia de dependências in-line para manter o teste
# auto-contido (sem fixtures factory globais).
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_isolation_clinicacanal(tenant_a, clinica_b):
    with tenant_a() as clinica:
        canal_id = ClinicaCanal.objects.create(
            clinica=clinica,
            tipo=ClinicaCanal.Tipo.WHATSAPP_EVOLUTION,
            numero_e164="+5511999999991",
        ).id

    with _sessao_app_readwrite(clinica_b.id):
        assert not ClinicaCanal.objects.filter(id=canal_id).exists()


@pytest.mark.django_db(transaction=True)
def test_isolation_clinicapolitica(tenant_a, clinica_b):
    with tenant_a() as clinica:
        politica_id = ClinicaPolitica.objects.create(
            clinica=clinica,
            chave="cancelamento_antecedencia_h",
            valor=24,
        ).id

    with _sessao_app_readwrite(clinica_b.id):
        assert not ClinicaPolitica.objects.filter(id=politica_id).exists()


@pytest.mark.django_db(transaction=True)
def test_isolation_paciente(tenant_a, clinica_b):
    with tenant_a() as clinica:
        paciente_id = Paciente.objects.create(
            clinica=clinica,
            telefone_e164="+5511999999992",
            nome="Maria",
        ).id

    with _sessao_app_readwrite(clinica_b.id):
        assert not Paciente.objects.filter(id=paciente_id).exists()


@pytest.mark.django_db(transaction=True)
def test_isolation_especialidade(tenant_a, clinica_b):
    with tenant_a() as clinica:
        especialidade_id = Especialidade.objects.create(
            clinica=clinica,
            nome="Cardiologia",
        ).id

    with _sessao_app_readwrite(clinica_b.id):
        assert not Especialidade.objects.filter(id=especialidade_id).exists()


@pytest.mark.django_db(transaction=True)
def test_isolation_medico(tenant_a, clinica_b):
    with tenant_a() as clinica:
        medico_id = Medico.objects.create(
            clinica=clinica,
            nome="Dr. House",
            crm="111111/SP",
        ).id

    with _sessao_app_readwrite(clinica_b.id):
        assert not Medico.objects.filter(id=medico_id).exists()


@pytest.mark.django_db(transaction=True)
def test_isolation_convenio(tenant_a, clinica_b):
    with tenant_a() as clinica:
        convenio_id = Convenio.objects.create(
            clinica=clinica,
            nome="Unimed",
        ).id

    with _sessao_app_readwrite(clinica_b.id):
        assert not Convenio.objects.filter(id=convenio_id).exists()


@pytest.mark.django_db(transaction=True)
def test_isolation_medicoconvenio(tenant_a, clinica_b):
    """Through table com clinica_id desnormalizado: RLS própria isola."""
    with tenant_a() as clinica:
        medico = Medico.objects.create(
            clinica=clinica,
            nome="Dr. Strange",
            crm="222222/SP",
        )
        convenio = Convenio.objects.create(clinica=clinica, nome="Bradesco")
        medico_convenio_id = MedicoConvenio.objects.create(
            medico=medico,
            convenio=convenio,
        ).id

    with _sessao_app_readwrite(clinica_b.id):
        assert not MedicoConvenio.objects.filter(id=medico_convenio_id).exists()


@pytest.mark.django_db(transaction=True)
def test_isolation_medicodisponibilidade(tenant_a, clinica_b):
    """Through table com clinica_id desnormalizado: RLS própria isola."""
    with tenant_a() as clinica:
        medico = Medico.objects.create(
            clinica=clinica,
            nome="Dr. Watson",
            crm="333333/SP",
        )
        disponibilidade_id = MedicoDisponibilidade.objects.create(
            medico=medico,
            dia_semana=MedicoDisponibilidade.DiaSemana.SEGUNDA,
            inicio=time(8, 0),
            fim=time(12, 0),
        ).id

    with _sessao_app_readwrite(clinica_b.id):
        assert not MedicoDisponibilidade.objects.filter(id=disponibilidade_id).exists()


# ---------------------------------------------------------------------------
# Defesa em profundidade — tentar salvar com clinica_id ≠ app.clinica_id
# dispara ValidationError no TenantAwareModel.save() ANTES de chegar no DB.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_clinicacanal_save_rejeita_clinica_id_diferente_da_sessao(clinica_a, clinica_b):
    with tenant_session(clinica_a.id):
        with pytest.raises(ValidationError):
            ClinicaCanal(
                clinica=clinica_b,
                tipo=ClinicaCanal.Tipo.WHATSAPP_EVOLUTION,
                numero_e164="+5511777777777",
            ).save()


@pytest.mark.django_db(transaction=True)
def test_clinicapolitica_save_rejeita_clinica_id_diferente_da_sessao(
    clinica_a, clinica_b
):
    with tenant_session(clinica_a.id):
        with pytest.raises(ValidationError):
            ClinicaPolitica(
                clinica=clinica_b,
                chave="cpf_obrigatorio",
                valor=True,
            ).save()


@pytest.mark.django_db(transaction=True)
def test_paciente_save_rejeita_clinica_id_diferente_da_sessao(clinica_a, clinica_b):
    with tenant_session(clinica_a.id):
        with pytest.raises(ValidationError):
            Paciente(
                clinica=clinica_b,
                telefone_e164="+5511666666666",
                nome="João",
            ).save()


@pytest.mark.django_db(transaction=True)
def test_especialidade_save_rejeita_clinica_id_diferente_da_sessao(
    clinica_a, clinica_b
):
    with tenant_session(clinica_a.id):
        with pytest.raises(ValidationError):
            Especialidade(clinica=clinica_b, nome="Pediatria").save()


@pytest.mark.django_db(transaction=True)
def test_medico_save_rejeita_clinica_id_diferente_da_sessao(clinica_a, clinica_b):
    with tenant_session(clinica_a.id):
        with pytest.raises(ValidationError):
            Medico(
                clinica=clinica_b,
                nome="Dr. Estranho",
                crm="999999/SP",
            ).save()


@pytest.mark.django_db(transaction=True)
def test_convenio_save_rejeita_clinica_id_diferente_da_sessao(clinica_a, clinica_b):
    with tenant_session(clinica_a.id):
        with pytest.raises(ValidationError):
            Convenio(clinica=clinica_b, nome="Amil").save()


@pytest.mark.django_db(transaction=True)
def test_medicoconvenio_save_rejeita_clinica_id_de_outro_medico(clinica_a, clinica_b):
    """Como `clinica_id` é auto-populado a partir do FK pai, o
    cenário de violação aqui é: criar `Medico` na clínica B,
    abrir sessão na clínica A, e tentar salvar `MedicoConvenio`
    do médico de B. O auto-popular vai setar
    `clinica_id = clinica_b.id`, e a validação do `save()` aborta
    porque a sessão é da A.
    """
    with tenant_session(clinica_b.id):
        medico_b = Medico.objects.create(
            clinica=clinica_b, nome="Dr. B", crm="555555/SP"
        )
        convenio_b = Convenio.objects.create(clinica=clinica_b, nome="SulAmérica")

    with tenant_session(clinica_a.id):
        with pytest.raises(ValidationError):
            MedicoConvenio(medico=medico_b, convenio=convenio_b).save()


@pytest.mark.django_db(transaction=True)
def test_medicodisponibilidade_save_rejeita_clinica_id_de_outro_medico(
    clinica_a, clinica_b
):
    """Mesmo padrão de `MedicoConvenio`: o `save()` aborta quando
    `clinica_id` herdado do `Medico` não bate com a sessão atual."""
    with tenant_session(clinica_b.id):
        medico_b = Medico.objects.create(
            clinica=clinica_b, nome="Dr. B", crm="444444/SP"
        )

    with tenant_session(clinica_a.id):
        with pytest.raises(ValidationError):
            MedicoDisponibilidade(
                medico=medico_b,
                dia_semana=MedicoDisponibilidade.DiaSemana.QUARTA,
                inicio=time(9, 0),
                fim=time(12, 0),
            ).save()
