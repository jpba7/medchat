"""Concede GRANTs para `app_readwrite`/`app_jobs` e ensina o helper
`apply_rls_policy()` a fazer o mesmo para tabelas futuras.

Achado durante os testes de isolation: o user `medchat` (owner do
banco no docker-compose) é SUPERUSER + BYPASSRLS, então RLS é
ignorada quando a aplicação roda como ele. Em produção, Django
deve conectar como `app_readwrite` (sem privilégio de bypass) — mas
até esta migration, esse role não tinha GRANT em nada e nem poderia
ler/escrever.

Esta migration corrige a base:

1. Atualiza `apply_rls_policy(regclass)` para também conceder
   `SELECT, INSERT, UPDATE, DELETE` na tabela alvo a `app_readwrite`
   e `app_jobs` — futuras tabelas tenant-aware ganham o GRANT junto
   com a policy, sem ato extra.

2. Concede `USAGE` no schema `public` aos dois roles (sem isso,
   nem GRANT em tabela permite tocar nelas).

3. Aplica os GRANTs explicitamente nas 9 tabelas que JÁ existem
   (a global `clinicas` + as 8 tenant-aware da Onda 1) — essas não
   chamarão `apply_rls_policy` de novo, então precisam do GRANT
   atribuído aqui.

Em produção ainda falta um passo (fora do escopo desta migration):
trocar a `DATABASE_URL` para conectar como `app_readwrite` em vez
do owner. Migrations continuam sendo aplicadas com o user owner
(precisam de DDL).
"""

from django.db import migrations


# Atualiza a função pra incluir GRANT no fluxo padrão.
UPDATE_APPLY_RLS_POLICY_SQL = r"""
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
    EXECUTE format(
        'GRANT SELECT, INSERT, UPDATE, DELETE ON %s TO app_readwrite, app_jobs',
        target_table
    );
END;
$fn$;
"""

# Reverter para a versão sem GRANT (preserva drop_rls_policy intacto).
REVERT_APPLY_RLS_POLICY_SQL = r"""
CREATE OR REPLACE FUNCTION apply_rls_policy(target_table regclass)
RETURNS void
LANGUAGE plpgsql
AS $fn$
BEGIN
    EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', target_table);
    EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', target_table);
    EXECUTE format(
        'CREATE POLICY tenant_isolation ON %s '
        'USING (clinica_id = current_setting(''app.clinica_id'')::uuid) '
        'WITH CHECK (clinica_id = current_setting(''app.clinica_id'')::uuid)',
        target_table
    );
END;
$fn$;
"""


# USAGE no schema é pré-requisito para qualquer GRANT em tabela funcionar.
GRANT_SCHEMA_SQL = "GRANT USAGE ON SCHEMA public TO app_readwrite, app_jobs;"
REVOKE_SCHEMA_SQL = "REVOKE USAGE ON SCHEMA public FROM app_readwrite, app_jobs;"


# Tabelas que já existem no momento desta migration. `clinicas` é
# global mas `app_readwrite` precisa lê-la (para o middleware
# resolver o tenant via slug antes de SET LOCAL).
GRANT_EXISTING_TABLES_SQL = r"""
GRANT SELECT ON clinicas TO app_readwrite, app_jobs;
GRANT SELECT, INSERT, UPDATE, DELETE ON
    clinica_canais,
    clinica_politicas,
    pacientes,
    especialidades,
    medicos,
    convenios,
    medico_convenios,
    medico_disponibilidades
TO app_readwrite, app_jobs;
"""

REVOKE_EXISTING_TABLES_SQL = r"""
REVOKE SELECT ON clinicas FROM app_readwrite, app_jobs;
REVOKE SELECT, INSERT, UPDATE, DELETE ON
    clinica_canais,
    clinica_politicas,
    pacientes,
    especialidades,
    medicos,
    convenios,
    medico_convenios,
    medico_disponibilidades
FROM app_readwrite, app_jobs;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_rls_setup"),
        # Garante que todas as tabelas alvo existem antes do GRANT.
        ("clinics", "0002_clinicacanal_clinicapolitica"),
        ("patients", "0001_initial"),
        ("catalog", "0002_medicoconvenio_medicodisponibilidade"),
    ]

    operations = [
        migrations.RunSQL(
            sql=UPDATE_APPLY_RLS_POLICY_SQL,
            reverse_sql=REVERT_APPLY_RLS_POLICY_SQL,
        ),
        migrations.RunSQL(
            sql=GRANT_SCHEMA_SQL,
            reverse_sql=REVOKE_SCHEMA_SQL,
        ),
        migrations.RunSQL(
            sql=GRANT_EXISTING_TABLES_SQL,
            reverse_sql=REVOKE_EXISTING_TABLES_SQL,
        ),
    ]
