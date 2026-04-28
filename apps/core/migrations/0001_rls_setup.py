"""Cria a infraestrutura SQL de multi-tenancy do MedChat:

1. Roles Postgres
   - `app_readwrite` (sem `BYPASSRLS`) — role pretendida para a
     aplicação Django em produção. Sob policy RLS.
   - `app_jobs` (com `BYPASSRLS`) — role para Celery tasks
     cross-tenant (lembretes diários, expurgo). Bypassa policy
     EXPLICITAMENTE; nunca usar em código tenant-aware.
   Dev local usa o owner `medchat` definido no compose; estes roles
   só ganham `LOGIN` + senha em produção, via `ALTER ROLE`.

2. Função `apply_rls_policy(target_table regclass)` — helper que
   migrations futuras vão chamar para ativar RLS em cada tabela
   tenant-owned conforme forem criadas. Centraliza o padrão (ENABLE
   + FORCE + policy `tenant_isolation`) num único lugar; se a regra
   mudar (ex.: adicionar `BYPASSRLS` por role admin), trocamos só
   aqui e novas migrations herdam.

3. Função `drop_rls_policy(target_table regclass)` — inverso, útil
   em rollback.

Migrations de tabelas tenant-owned chamarão (depois do `CreateModel`):

    operations = [
        migrations.CreateModel(...),
        migrations.RunSQL(
            "SELECT apply_rls_policy('pacientes');",
            reverse_sql="SELECT drop_rls_policy('pacientes');",
        ),
    ]
"""

from django.db import migrations


# DO + IF NOT EXISTS torna a migration idempotente — útil quando o
# Postgres é compartilhado entre ambientes ou quando a migration é
# aplicada parcialmente e precisa ser re-rodada.
CREATE_ROLES_SQL = r"""
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_readwrite') THEN
        CREATE ROLE app_readwrite NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_jobs') THEN
        CREATE ROLE app_jobs NOLOGIN BYPASSRLS;
    END IF;
END
$$;
"""

DROP_ROLES_SQL = r"""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_readwrite') THEN
        DROP ROLE app_readwrite;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_jobs') THEN
        DROP ROLE app_jobs;
    END IF;
END
$$;
"""


# A função usa `format` com `regclass` em vez de string crua para que
# o nome da tabela seja propriamente quotado e checado contra
# search_path. Isso bloqueia SQL injection trivial e dá erro claro
# se a tabela não existir.
CREATE_APPLY_RLS_POLICY_SQL = r"""
CREATE OR REPLACE FUNCTION apply_rls_policy(target_table regclass)
RETURNS void
LANGUAGE plpgsql
AS $fn$
BEGIN
    EXECUTE format(
        'ALTER TABLE %s ENABLE ROW LEVEL SECURITY',
        target_table
    );
    EXECUTE format(
        'ALTER TABLE %s FORCE ROW LEVEL SECURITY',
        target_table
    );
    EXECUTE format(
        'CREATE POLICY tenant_isolation ON %s '
        'USING (clinica_id = current_setting(''app.clinica_id'')::uuid) '
        'WITH CHECK (clinica_id = current_setting(''app.clinica_id'')::uuid)',
        target_table
    );
END;
$fn$;
"""

DROP_APPLY_RLS_POLICY_SQL = "DROP FUNCTION IF EXISTS apply_rls_policy(regclass);"


CREATE_DROP_RLS_POLICY_SQL = r"""
CREATE OR REPLACE FUNCTION drop_rls_policy(target_table regclass)
RETURNS void
LANGUAGE plpgsql
AS $fn$
BEGIN
    EXECUTE format(
        'DROP POLICY IF EXISTS tenant_isolation ON %s',
        target_table
    );
    EXECUTE format(
        'ALTER TABLE %s NO FORCE ROW LEVEL SECURITY',
        target_table
    );
    EXECUTE format(
        'ALTER TABLE %s DISABLE ROW LEVEL SECURITY',
        target_table
    );
END;
$fn$;
"""

DROP_DROP_RLS_POLICY_SQL = "DROP FUNCTION IF EXISTS drop_rls_policy(regclass);"


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.RunSQL(
            sql=CREATE_ROLES_SQL,
            reverse_sql=DROP_ROLES_SQL,
        ),
        migrations.RunSQL(
            sql=CREATE_APPLY_RLS_POLICY_SQL,
            reverse_sql=DROP_APPLY_RLS_POLICY_SQL,
        ),
        migrations.RunSQL(
            sql=CREATE_DROP_RLS_POLICY_SQL,
            reverse_sql=DROP_DROP_RLS_POLICY_SQL,
        ),
    ]
