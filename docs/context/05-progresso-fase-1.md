---
name: Progresso da Fase 1
description: Estado atual da execução da Fase 1 — checklist com o que está feito, em andamento e pendente.
status: em-andamento
ultima_atualizacao: 2026-04-29
---

# Progresso — Fase 1 (Fundação Django)

Plano completo em [`../plans/01-fundacao-fase-1.md`](../plans/01-fundacao-fase-1.md).

## Legenda
- ✅ feito
- ⏳ em andamento
- ❌ pendente

## Checklist de execução

### 0. Pré-requisitos do ambiente
- ✅ Docker 29.2.1 instalado e funcionando
- ✅ Docker Compose v5.0.2
- ✅ Python 3.13.13
- ✅ git 2.47
- ✅ `uv` 0.11.8 instalado em `C:\Users\peedr\.local\bin\` e adicionado ao PATH do user

### 1. Setup inicial do repositório (`uv` + Django scaffold)

- ✅ `C:\Repos\medchat\` criado
- ✅ `git init -b main`
- ✅ `uv init --bare` — `pyproject.toml` mínimo gerado
- ✅ `uv python pin 3.13` — `.python-version` fixou Python 3.13
- ✅ Estrutura de pastas docs criada: `docs/{context,adr,ai-engineering,plans}/`
- ✅ `README.md` na raiz
- ✅ `.gitignore` para Python+Django+Docker+uv com camadas anti-vazamento de secret
- ✅ `CLAUDE.md` com regras e estilo de trabalho
- ✅ Plano + memórias da sessão anterior copiados para `docs/plans/` e `docs/context/`
- ✅ `uv add` das dependências principais (Django 6, Ninja, psycopg, redis, celery, anthropic, openai, langfuse, pgtrigger, etc) — `pyproject.toml` + `uv.lock` versionados

### 2. Django scaffold
- ✅ `django-admin startproject config .` (layout flat, raiz do repo)
- ✅ Settings modular `config/settings/{base,dev,prod,test}.py`
- ✅ `django-environ` lendo `.env`
- ✅ `.env.example` versionado

### 3. Estrutura de apps Django (9 apps)
- ✅ `apps/core` — `TenantAwareModel`, `RLSMiddleware`, `with_tenant`, migrations RLS (0001 setup + 0002 GRANTs)
- ✅ `apps/clinics` — `Clinica`, `ClinicaCanal`, `ClinicaPolitica`
- ✅ `apps/patients` — `Paciente`
- ✅ `apps/catalog` — `Especialidade`, `Medico`, `Convenio`, `MedicoConvenio`, `MedicoDisponibilidade`
- ✅ `apps/appointments` — `Agendamento` + exclusion constraint anti-overlap (`EXCLUDE USING GIST` com `btree_gist`)
- ✅ `apps/conversations` — `Conversa`, `Mensagem`, `Handoff` (+ unique parcial `(canal, external_id) WHERE external_id IS NOT NULL` em `mensagens` para idempotência de webhook)
- ❌ `apps/bot` — scaffolding (Fase 2 implementa)
- ⏳ `apps/channels` — `Outbox` ✅; providers WhatsApp + webhook entry ❌
- ⏳ `apps/observability` — `EventoBot` ✅; Langfuse client, health, metrics ❌

### 4. Documentação pedagógica
- ❌ `docs/adr/0001-django-vs-n8n.md`
- ✅ `docs/adr/0002-rls-vs-schema.md`
- ❌ `docs/adr/0003-anthropic-openrouter.md`
- ❌ `docs/ai-engineering/01-por-que-nao-n8n.md`
- ❌ `docs/ai-engineering/02-primeira-chamada-anthropic.md`
- ❌ `docs/ai-engineering/03-system-prompts-estruturados.md`
- ❌ `docs/ai-engineering/04-prompt-caching-anthropic.md`
- ❌ `docs/ai-engineering/05-tool-use-fundamentos.md`
- ❌ `docs/ai-engineering/06-observabilidade-langfuse.md`
- ✅ `docs/ai-engineering/07-multi-tenant-rls-postgres.md`

### 5. Stack de containers
- ✅ `Dockerfile` (python:3.13-slim + uv 0.11.8 com BuildKit cache mounts)
- ✅ `docker-compose.yml` com 6 serviços: postgres (pgvector/pg17), redis, langfuse-db, langfuse, web, worker, beat
- ✅ `Makefile` com atalhos (`up`, `down`, `build`, `logs`, `migrate`, `shell`, `test`, `lint`, `format`, `clean`)
- ✅ `pytest.ini` + `conftest.py` raiz com fixtures multi_tenant

### 6. Multi-tenancy (RLS)
- ✅ `apps/core/models.py` — `TenantAwareModel` abstract com validação no `save()`
- ✅ `apps/core/middleware.py` — `RLSMiddleware` (resolve via `X-Clinic-Slug`; fail-loud 500)
- ✅ `apps/core/tenancy.py` — `tenant_session` (context manager) + `@with_tenant` (decorator Celery)
- ✅ `apps/core/migrations/0001_rls_setup.py` — roles `app_readwrite`/`app_jobs` + helper `apply_rls_policy()`
- ✅ `apps/core/migrations/0002_grants_app_roles.py` — atualiza helper para conceder GRANT junto com a policy + GRANTs explícitos nas 9 tabelas existentes (descoberto via teste: `medchat` é SUPERUSER + BYPASSRLS, então prod precisa conectar como `app_readwrite` para RLS aplicar)
- ✅ Migration base de `clinicas` (sem RLS — é raiz da tenancy, intencional)
- ✅ Migrations base: `clinica_canais`, `clinica_politicas` com policies RLS

### 7. Migrations de domínio
- ✅ Onda 1 (cadastro): `clinica_canais`, `clinica_politicas`, `pacientes`, `especialidades`, `medicos`, `convenios`, `medico_convenios`, `medico_disponibilidades` — todas com RLS aplicada
- ✅ Onda 2 (`agendamentos`): `CheckConstraint` (inicio<fim) + `ExclusionConstraint` `EXCLUDE USING GIST (medico_id WITH =, tstzrange(inicio_em, fim_em) WITH &&) WHERE status != 'cancelado'` (extension `btree_gist`) + RLS aplicada
- ✅ Onda 3 (`conversas`, `mensagens`, `handoffs`): `UniqueConstraint` parcial `(canal, external_id) WHERE external_id IS NOT NULL` em mensagens — idempotência de webhook ao nível DB. RLS aplicada nas 3 tabelas. `clinica_id` desnormalizado em mensagens/handoffs (auto-populated do FK `conversa`).
- ✅ Onda 4 (`outbox` em `apps.channels`, `eventos_bot` em `apps.observability`): outbox pattern para envio assíncrono ao provedor (status enum + retry exponencial via `tentativas`/`proxima_em`); EventoBot é log estruturado complementar ao Langfuse, com FK opcional pra `Conversa` (SET_NULL para preservar evento histórico). RLS aplicada nas 2 tabelas.

### 8. API HTTP (Ninja)
- ❌ `config/api.py` — NinjaAPI raiz
- ❌ `GET /api/health` — Postgres + Redis + Celery checks
- ❌ `GET /api/ready` — só Postgres
- ❌ `POST /api/webhooks/whatsapp/{canal_id}` — valida HMAC, idempotência, dispatch Celery
- ❌ `POST /api/webhooks/langfuse` — stub (Fase 3)

### 9. Celery + tarefas
- ❌ `config/celery.py`
- ❌ Task `process_inbound_message` (eco MVP "Recebi. Em instantes respondo.")
- ❌ Task `send_outbox` (consumidor FIFO por conversa)
- ❌ `django-celery-beat` migrations

### 10. Adapter WhatsApp
- ❌ `apps/channels/providers/base.py` — Protocol `WhatsAppProvider`, dataclasses
- ❌ `apps/channels/providers/evolution.py` — implementação completa
- ❌ `apps/channels/providers/cloud.py` — stub `NotImplementedError`
- ❌ Factory `get_provider(canal)`

### 11. Observabilidade (Langfuse)
- ❌ `apps/observability/langfuse.py` — client singleton
- ❌ Primeiro trace manual no webhook
- ❌ Health endpoint completo

### 12. Testes
- ⏳ `tests/integration/test_rls.py` — **40 testes verdes**: 8 fundação + 8 isolation Onda 1 + 8 defesa em profundidade Onda 1 + 4 Agendamento (Onda 2) + 8 Onda 3 (com idempotência) + 4 Onda 4 (Outbox + EventoBot, isolation + defesa em profundidade). Cobertura completa do item 7. Próximas baterias: webhook idempotency, Evolution provider — quando os endpoints/clientes existirem.
- ❌ `tests/integration/test_webhook_idempotency.py`
- ❌ `tests/integration/test_evolution_provider.py`
- ❌ `tests/fixtures/evolution_webhooks/` com payloads reais

### 13. Verificação end-to-end
- ⏳ `make up` em <5min em máquina nova — stack sobe limpo (postgres, redis, langfuse-db, langfuse, web healthy; worker/beat esperadamente exit-2 até item 9 entregar `config/celery.py`)
- ✅ `make test` ≥ 30 testes verdes (≥ 10 RLS) — **40/40 verdes hoje** (32 RLS + 1 anti-overlap real + 1 idempotência); critério atingido
- ❌ Smoke: WhatsApp → eco em <10s, trace no Langfuse
- ❌ Isolation manual com `psql` em duas clínicas
- ❌ `docker build` da imagem prod boota com `.env.prod.example`
- ❌ **Pendência crítica de hardening**: aplicação Django ainda conecta como `medchat` (owner, SUPERUSER+BYPASSRLS). Em produção, trocar a `DATABASE_URL` para usar `app_readwrite` (sem privilégio de bypass). Sem isso, RLS é ignorada em runtime apesar das policies estarem corretas.

## Próximo passo concreto

Onda 1 do item 7 fechada (8 modelos de cadastro tenant-aware com RLS comprovada por testes). Stack roda contra Postgres real, 24 testes verdes. Validações:

- `docker compose ps` → 5 containers healthy (postgres com pgvector 0.8.2, redis, langfuse-db, langfuse, web)
- `uv run python manage.py migrate` → aplica todas migrations sem erro
- `uv run pytest tests/ -v` → **24/24 verdes em ~4s** (16 RLS)
- `psql -c "\dt"` no medchat-postgres → 9 tabelas tenant-aware/global do MedChat + tabelas Django/celery_beat
- `psql -c "SELECT relname, relrowsecurity FROM pg_class WHERE ..."` → todas as 8 tenant-aware com `relrowsecurity=t`

Próximas frentes (em ordem sugerida):

1. **`config/celery.py`** (item 9) — destrava worker/beat (hoje saem com exit 2 — `Module 'config' has no attribute 'celery'`). Pré-requisito pras tasks `process_inbound_message` (consumir webhook) e `send_outbox` (drenar outbox pra provedor com retry).
2. **`config/api.py` + `GET /api/health`** (item 8) — primeiro endpoint Ninja, valida Postgres+Redis+Celery end-to-end.
3. **`POST /api/webhooks/whatsapp/{canal_id}`** (item 8) — usa o `webhook_secret` de `ClinicaCanal` para HMAC + a unique parcial `(canal, external_id)` para idempotência. Roteia pra Celery via `process_inbound_message`.
4. **EvolutionProvider** (item 10) — HTTP client + parser webhook + send. Primeiro provider real do `apps.channels`.
5. **Langfuse client + primeiro trace** (item 11) em `apps.observability`.
6. **ADRs faltantes**: 0001 (Django vs n8n) e 0003 (Anthropic + OpenRouter) para fechar o trio fundacional.
7. **Hardening: trocar `DATABASE_URL` para `app_readwrite`** em produção (item 13 último marcador) — habilita RLS de verdade em runtime, hoje ela só aplica nos testes via `SET LOCAL ROLE`.

Critério para encerrar a Fase 1 (todos os 10 pontos do plano em
[`../plans/01-fundacao-fase-1.md`](../plans/01-fundacao-fase-1.md)
seção "Critérios de conclusão"). Falta ainda webhook WhatsApp,
Evolution provider, Langfuse client, health endpoint, eco MVP e
testes E2E.
