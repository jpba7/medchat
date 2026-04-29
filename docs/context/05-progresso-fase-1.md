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
- ✅ `apps/core` — `TenantAwareModel`, `RLSMiddleware`, `with_tenant`, migration RLS
- ⏳ `apps/clinics` — `Clinica` ✅; `ClinicaCanal` e `ClinicaPolitica` ❌
- ❌ `apps/patients` — `Paciente`
- ❌ `apps/catalog` — `Especialidade`, `Medico`, `Convenio`, `Disponibilidade`
- ❌ `apps/appointments` — `Agendamento` + exclusion constraint
- ❌ `apps/conversations` — `Conversa`, `Mensagem`, `Handoff`
- ❌ `apps/bot` — scaffolding (Fase 2 implementa)
- ❌ `apps/channels` — providers WhatsApp + webhook entry
- ❌ `apps/observability` — Langfuse client, health, metrics

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
- ✅ Migration base de `clinicas` (sem RLS — é raiz da tenancy, intencional)
- ❌ Migrations base: `clinica_canais`, `clinica_politicas` com policies RLS

### 7. Migrations de domínio
- ❌ `pacientes`, `especialidades`, `medicos`, `convenios`, `medico_convenios`, `medico_disponibilidades`
- ❌ `agendamentos` com exclusion constraint `btree_gist`
- ❌ `conversas`, `mensagens` (unique `(canal_id, external_id)`), `handoffs`
- ❌ `outbox`, `eventos_bot`

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
- ⏳ `tests/integration/test_rls.py` — fundação coberta (8 testes: roles, helpers `apply_rls_policy`/`drop_rls_policy`, `tenant_session`, `@with_tenant`, `Clinica` global). Falta ≥ 1 caso por tabela tenant-owned (depende do item 7 — quando `Paciente`, `Medico` etc. existirem).
- ❌ `tests/integration/test_webhook_idempotency.py`
- ❌ `tests/integration/test_evolution_provider.py`
- ❌ `tests/fixtures/evolution_webhooks/` com payloads reais

### 13. Verificação end-to-end
- ⏳ `make up` em <5min em máquina nova — stack sobe limpo (postgres, redis, langfuse-db, langfuse, web healthy; worker/beat esperadamente exit-2 até item 9 entregar `config/celery.py`)
- ⏳ `make test` ≥ 30 testes verdes (≥ 10 RLS) — 8/8 RLS passando hoje; total final só após itens 7-11
- ❌ Smoke: WhatsApp → eco em <10s, trace no Langfuse
- ❌ Isolation manual com `psql` em duas clínicas
- ❌ `docker build` da imagem prod boota com `.env.prod.example`

## Próximo passo concreto

Stack já está de pé contra Postgres real (após recuperação do Docker em 2026-04-29 — snapshotter overlayfs do containerd ficou corrompido depois de um `wsl --shutdown` no meio de uma operação de write; resolvido com `Clean / Purge data` via UI do Docker Desktop). Validações já passando:

- `docker compose ps` → 5 containers healthy (postgres com pgvector 0.8.2, redis, langfuse-db, langfuse, web)
- `uv run python manage.py migrate` → aplica `core/0001_rls_setup` + `clinics/0001_initial` + 19 do `django_celery_beat`
- `uv run pytest tests/integration/test_rls.py -v` → 8/8 verdes em ~2s
- `curl http://localhost:8000/admin/` → HTTP 302 (uvicorn OK)
- `curl http://localhost:3000` → HTTP 200 (langfuse OK)

Próximas frentes (em ordem sugerida):

1. **Tabelas tenant-owned com RLS aplicada via helper** (item 7):
   - `apps/clinics`: `ClinicaCanal`, `ClinicaPolitica`.
   - `apps/patients`: `Paciente`.
   - `apps/catalog`: `Especialidade`, `Medico`, `Convenio`,
     `MedicoConvenio`, `MedicoDisponibilidade`.
   - Cada migration: `CreateModel` + `RunSQL("SELECT
     apply_rls_policy('<tabela>');")`.
   - Adicionar 1 teste de isolation por tabela em `tests/integration/test_rls.py`.
2. **`config/celery.py`** (item 9) para destravar worker/beat. Hoje saem com exit 2 — `Module 'config' has no attribute 'celery'`. Sem isso, nem dá pra rodar a primeira task `process_inbound_message`.
3. **ADR-001** (Django vs n8n) e **ADR-003** (Anthropic + OpenRouter) para fechar o trio fundacional.
4. **`config/api.py` + `GET /api/health`** (item 8) — primeiro endpoint Ninja, valida Postgres+Redis end-to-end.

Critério para encerrar a Fase 1 (todos os 10 pontos do plano em
[`../plans/01-fundacao-fase-1.md`](../plans/01-fundacao-fase-1.md)
seção "Critérios de conclusão"). Falta ainda webhook WhatsApp,
Evolution provider, Langfuse client, health endpoint, eco MVP e
testes E2E.
