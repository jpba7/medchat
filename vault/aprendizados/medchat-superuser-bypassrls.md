---
name: medchat-superuser-bypassrls
type: aprendizado
tags: [rls, postgres, seguranca, prod-blocker]
---

# Aprendizado: user `medchat` do compose é SUPERUSER + BYPASSRLS — RLS é silenciosamente ignorada

> Em desenvolvimento local, todas as queries da app passam por RLS **na intenção** mas não **na prática** — o user que conecta tem `BYPASSRLS`, então as policies nunca rodam.

## O que descobrimos

O `docker-compose.yml` usa `POSTGRES_USER=medchat` (default Postgres). Esse user nasce como **SUPERUSER** — em Postgres, SUPERUSER é automaticamente `BYPASSRLS`. Quando o Django conecta via `DATABASE_URL` apontando pra esse user, **as policies RLS são puladas silenciosamente**:

```sql
-- A policy existe e tá ativa:
SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'pacientes';
-- (t, t)

-- Mas conectado como SUPERUSER, a query retorna TUDO:
SELECT * FROM pacientes;
-- (todas as linhas de todas as clínicas)
```

Não é warning. Não é erro. **Sucesso silencioso, com vazamento total.**

## Como descobrimos

Os primeiros testes RLS escritos (commit `f191d5c`) passavam, mas só validavam o **setup** (`relrowsecurity = t`, policy existe, `app.clinica_id` pode ser setado). Não exercitavam a policy contra dados.

Quando escrevi os testes de **isolation cross-tenant** (commit `b8e6418`), eles começaram retornando linhas de todas as clínicas — sinal clássico de RLS sendo bypassada.

Solução: testes usam `SET LOCAL ROLE app_readwrite` antes de cada query — força a sessão a operar como role sem BYPASSRLS, expondo o comportamento real:

```python
with connection.cursor() as cur:
    cur.execute("SET LOCAL ROLE app_readwrite")
    cur.execute("SET LOCAL app.clinica_id = %s", [str(clinica_a.id)])
    # agora SELECT só vê linhas da clinica_a
```

## Implicação

**Em produção, conectar como `medchat` é vazamento garantido.** Hardening pendente:

- **Em prod**: `DATABASE_URL` deve apontar pra `app_readwrite` (sem SUPERUSER, sem BYPASSRLS). Roles criados pela migration `core/0001_rls_setup`.
- **Tasks Celery**: precisam do role `app_jobs` (também sem BYPASSRLS) com decorator `@with_tenant` que seta `app.clinica_id` antes da query.
- **Migrations e admin Django**: aí sim usam SUPERUSER (precisam BYPASSRLS pra criar tabelas, rodar `apply_rls_policy`, etc.).

Sem essa troca, **RLS é só intenção em runtime** — funciona em testes (que forçam o role) e quebra em produção (onde o role real é SUPERUSER).

## Onde já apareceu

- Migration `apps/core/migrations/0001_rls_setup.py` — cria roles `app_readwrite` e `app_jobs`.
- Migration `apps/core/migrations/0002_grants_app_roles.py` (commit `82cc114`) — dá GRANT nas tabelas pros roles.
- Testes em `tests/integration/test_rls.py` — usam `SET LOCAL ROLE app_readwrite` em todos os testes de isolation.

## Próxima vez que importar

Quando preparar deploy Railway / produção:

1. Variáveis `DATABASE_URL_APP` (`app_readwrite`) e `DATABASE_URL_JOBS` (`app_jobs`) separadas do `DATABASE_URL_ADMIN` (SUPERUSER pra migrations).
2. Settings Django carregam por contexto: web request usa `_APP`, Celery worker usa `_JOBS`, `manage.py migrate` usa `_ADMIN`.
3. Smoke test em prod: rodar query num teste que valida **`current_user`** dentro da sessão Django — esperar `app_readwrite`, não `medchat`.

## Status

- [x] Confirmado — RLS funciona quando role correto é usado, ignorada com SUPERUSER. Testes provam ambos.
- [ ] Pendente: aplicar em prod. Hoje só dev local + CI usam o role correto via testes.

## Notas relacionadas

- [[../entidades/clinica]] — `Clinica` é a tabela GLOBAL (sem RLS, intencional)
- [[grant-faltava-na-migration]] — bug relacionado: roles existiam mas não tinham GRANT
- [[../decisoes/clinica-id-desnormalizado-vs-fk]] — defesa em profundidade: cada tabela RLS própria

## Referências externas

- [Postgres RLS docs](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [`docs/ai-engineering/07-multi-tenant-rls-postgres.md`](../../docs/ai-engineering/07-multi-tenant-rls-postgres.md) — pedagogia longa
