---
name: Progresso da Fase 1
description: Estado atual da execução da Fase 1 — checklist com o que está feito, em andamento e pendente.
status: em-andamento
ultima_atualizacao: 2026-04-27
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
- ❌ `uv add` das dependências principais (Django, Ninja, psycopg, redis, celery, anthropic, langfuse, etc)

### 2. Django scaffold
- ❌ `django-admin startproject config medchat/` (ou flat — confirmar layout)
- ❌ Settings modular `config/settings/{base,dev,prod,test}.py`
- ❌ `django-environ` lendo `.env`
- ❌ `.env.example` versionado

### 3. Estrutura de apps Django (9 apps)
- ❌ `apps/core` — TenantAwareModel, RLSMiddleware, with_tenant
- ❌ `apps/clinics` — Clinica, ClinicaCanal, ClinicaPolitica
- ❌ `apps/patients` — Paciente
- ❌ `apps/catalog` — Especialidade, Medico, Convenio, Disponibilidade
- ❌ `apps/appointments` — Agendamento + exclusion constraint
- ❌ `apps/conversations` — Conversa, Mensagem, Handoff
- ❌ `apps/bot` — scaffolding (Fase 2 implementa)
- ❌ `apps/channels` — providers WhatsApp + webhook entry
- ❌ `apps/observability` — Langfuse client, health, metrics

### 4. Documentação pedagógica
- ❌ `docs/adr/0001-django-vs-n8n.md`
- ❌ `docs/adr/0002-rls-vs-schema.md`
- ❌ `docs/adr/0003-anthropic-openrouter.md`
- ❌ `docs/ai-engineering/01-por-que-nao-n8n.md`
- ❌ `docs/ai-engineering/02-primeira-chamada-anthropic.md`
- ❌ `docs/ai-engineering/03-system-prompts-estruturados.md`
- ❌ `docs/ai-engineering/04-prompt-caching-anthropic.md`
- ❌ `docs/ai-engineering/05-tool-use-fundamentos.md`
- ❌ `docs/ai-engineering/06-observabilidade-langfuse.md`
- ❌ `docs/ai-engineering/07-multi-tenant-rls-postgres.md`

### 5. Stack de containers
- ❌ `Dockerfile` (python:3.13-slim + uv)
- ❌ `docker-compose.yml` com 7 serviços: postgres (pgvector/pg17), redis, langfuse-db, langfuse, web, worker, beat
- ❌ `Makefile` com atalhos (`up`, `down`, `migrate`, `test`, `lint`, `shell`, `logs`)
- ❌ `pytest.ini` + `conftest.py` raiz com fixtures multi_tenant

### 6. Multi-tenancy (RLS)
- ❌ `apps/core/models.py` — `TenantAwareModel` abstract
- ❌ `apps/core/middleware.py` — `RLSMiddleware`
- ❌ `apps/core/tenancy.py` — decorator `with_tenant` para Celery
- ❌ Migrations base: `clinicas`, `clinica_canais`, `clinica_politicas` com policies RLS

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
- ❌ `tests/integration/test_rls.py` — ≥ 1 caso por tabela tenant-owned
- ❌ `tests/integration/test_webhook_idempotency.py`
- ❌ `tests/integration/test_evolution_provider.py`
- ❌ `tests/fixtures/evolution_webhooks/` com payloads reais

### 13. Verificação end-to-end
- ❌ `make up` em <5min em máquina nova
- ❌ `make test` ≥ 30 testes verdes (≥ 10 RLS)
- ❌ Smoke: WhatsApp → eco em <10s, trace no Langfuse
- ❌ Isolation manual com `psql` em duas clínicas
- ❌ `docker build` da imagem prod boota com `.env.prod.example`

## Próximo passo concreto

**Adicionar dependências via `uv add`.** Lista completa no plano (Passo 1 do "Passo-a-passo de execução"). Sugestão de ordem:

1. Pacotes principais (Django, Ninja, psycopg, etc) — `uv add ...`
2. Pacotes dev (pytest, ruff) — `uv add --dev ...`
3. Verificar `uv.lock` foi gerado e commitar
4. Pausa pedagógica: explicar para que serve cada dependência principal

Em paralelo (opcional, mas pedagogicamente útil): criar **ADR-001** (Django vs n8n) e **ADR-002** (RLS vs schema-per-tenant) usando o template padrão (Status, Context, Decision, Consequences). Documentar enquanto a decisão ainda está fresca.
