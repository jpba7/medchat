# ADR-0002 — Isolamento multi-tenant via Row-Level Security do Postgres

## Status

Accepted — 2026-04-28.

## Context

MedChat é SaaS B2B multi-tenant: cada clínica é um tenant, e pacientes,
agendamentos, conversas e mensagens são tenant-owned. A regra inegociável
do produto é nunca expor dados de uma clínica para outra, mesmo em bug ou
request mal formada.

Três abordagens viáveis no Postgres:

1. **Shared DB / shared schema com `tenant_id`** — todas clínicas vivem
   nas mesmas tabelas, identificadas por `clinica_id`. Filtro é
   responsabilidade da aplicação (`Model.objects.filter(clinica_id=...)`).
2. **Shared DB / schema por tenant** — `CREATE SCHEMA clinica_X` por
   cliente; mesmas tabelas replicadas em cada schema; switch via
   `SET search_path`.
3. **DB por tenant** — banco completo por clínica.

A opção (1) é a mais barata, mas tem um risco enorme: um `WHERE` esquecido
ou um JOIN mal qualificado vaza dados. A opção (2) elimina o vazamento
mas multiplica o custo operacional — cada nova clínica é N tabelas
extras; toda mudança de schema vira loop por tenant. A opção (3) tem o
melhor isolamento mas o custo explode com 10+ clínicas e migrations
cross-DB são pesadelo.

Postgres oferece um superset da opção (1): **Row-Level Security** (RLS).
Em vez do filtro morar no Django, ele mora numa policy SQL que o banco
aplica em TODA query — `SELECT`, `UPDATE`, `DELETE`, `INSERT`. Se a
sessão não declarar quem é o tenant, queries filtram para zero linhas
(ou erram, dependendo da configuração). É enforcement no banco, não na
app — defesa em profundidade.

## Decision

Usar **shared DB / shared schema com Postgres RLS** como mecanismo
primário de isolamento multi-tenant. Combinado com:

- Coluna `clinica_id UUID NOT NULL` em toda tabela tenant-owned.
- Policy `tenant_isolation` em cada tabela tenant-owned:
  ```sql
  CREATE POLICY tenant_isolation ON pacientes
    USING (clinica_id = current_setting('app.clinica_id')::uuid)
    WITH CHECK (clinica_id = current_setting('app.clinica_id')::uuid);
  ```
- `RLSMiddleware` que abre `transaction.atomic()` por request e seta
  `SET LOCAL app.clinica_id = '<uuid>'` na conexão.
- Decorator `@with_tenant(clinica_id)` para Celery tasks (mesmo
  contrato fora do ciclo HTTP).
- Role `app_readwrite` (sob policy) para conexões da aplicação; role
  `app_jobs` (com `BYPASSRLS`) só para tasks cross-tenant explícitas
  (lembretes diários varrendo todas clínicas).
- `TenantAwareModel` abstract Django com FK `clinica` + validação no
  `save()` que bate `self.clinica_id` contra `current_setting`. Cinto
  e suspensório: se a app errar, o banco corta; se o banco for
  bypassado, a app corta.
- Fail-loud: se request tenant-aware chega sem tenant resolvido, aborta
  com 500 e log estruturado. Nunca retornar lista vazia silenciosamente.

## Consequences

**Positivas:**

- Migrations únicas, sem cópia por tenant.
- Provisionar clínica nova = `INSERT INTO clinicas`. Custo operacional
  por novo cliente é zero.
- Vazamento exige burlar SIMULTANEAMENTE policy SQL + middleware +
  validação no model — três camadas independentes.
- `BYPASSRLS` explícito permite jobs cross-tenant (Celery beat) sem
  hack ou disable temporário.
- `EXPLAIN ANALYZE` continua mostrando o filtro de RLS, fácil de
  debugar.

**Negativas:**

- **Silent fail mode:** se o app não resolver o tenant antes de
  consultar, queries retornam zero rows ou erram com mensagem genérica.
  Bug fantasma se middleware não rodar. *Mitigação:* middleware aborta
  500 quando não resolve tenant; teste `test_rls_fails_without_tenant`
  obrigatório no CI; logging estruturado em todo erro de policy.
- **Conexão pool + RLS:** worker pode pegar conexão com
  `app.clinica_id` da request anterior. *Mitigação:* `CONN_MAX_AGE=0`
  na Fase 1 (sem reuso de conexão) + `SET LOCAL` (escopo da transação,
  reseta no commit/rollback).
- **Performance:** policy é um filtro extra em toda query. Postgres
  trata como `WHERE` adicional; índice em `clinica_id` mantém custo
  proporcional ao tamanho do tenant, não da tabela. *Mitigação:*
  benchmark antes de assumir gargalo; Postgres lida bem com isso até
  centenas de tenants.
- **Não isola noisy-neighbor:** uma clínica fazendo 10k queries afeta
  latência das outras. *Mitigação:* rate-limit no app + monitoramento
  por tenant; não é problema na escala MVP.
- **Migrations precisam BYPASS:** `ALTER TABLE` em tabela com policy
  ativa exige role com `BYPASSRLS`. *Mitigação:* migrations Django
  rodam como super-user/owner em dev; em prod o role de migrations
  tem `BYPASSRLS`.

## Alternativas descartadas

- **Schema-per-tenant:** isolamento ótimo, custo operacional alto.
  Provisionar nova clínica = `CREATE SCHEMA + N CREATE TABLE`; toda
  migration vira loop. Inviável em produto que quer escalar pra
  centenas de clínicas com setup self-service no painel.
- **DB-per-tenant:** isolamento máximo, mas hosting e backup viram
  pesadelo a partir de ~10 clínicas. Migrations cross-DB exigem
  ferramentas extras (Atlas, Liquibase). Custo de Railway/AWS
  multiplica. Reservado para clientes enterprise no futuro distante.
- **Filtro só na app sem RLS:** simplest, mas confia 100% em
  disciplina humana. Um JOIN mal qualificado vaza. Inaceitável em
  produto regulado (LGPD, dados de saúde).

## Referências

- Postgres docs — Row Security Policies: <https://www.postgresql.org/docs/current/ddl-rowsecurity.html>
- Crunchy Data — "A Practical Guide to Multi-Tenant Postgres": <https://www.crunchydata.com/blog/postgres-row-level-security-for-multi-tenant-applications>
- ADR template (Michael Nygard): <https://github.com/joelparkerhenderson/architecture-decision-record>
- Nota didática companheira: [`docs/ai-engineering/07-multi-tenant-rls-postgres.md`](../ai-engineering/07-multi-tenant-rls-postgres.md)
