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
- ✅ `config/api.py` — NinjaAPI raiz, montada em `/api/` no `config/urls.py`
- ✅ `GET /api/health` — Postgres + Redis + Celery (`control.ping`) — retorna 200 (`status=ok`) ou 503 (`status=degraded`) + payload com check por dependência
- ✅ `GET /api/ready` — só Postgres (probe rápido para LB/k8s)
- ❌ `POST /api/webhooks/whatsapp/{canal_id}` — valida HMAC, idempotência, dispatch Celery
- ❌ `POST /api/webhooks/langfuse` — stub (Fase 3)

### 9. Celery + tarefas
- ✅ `config/celery.py` (Celery app + autodiscover) + `config/__init__.py` exporta `celery_app`
- ✅ Task `process_inbound_message` (eco MVP "Recebi. Em instantes respondo.") em `apps.conversations.tasks`
- ✅ Task `send_outbox` (consumidor com stub provider + esqueleto de retry exponencial 30s/2m/8m/32m/2h) em `apps.channels.tasks`
- ✅ `django-celery-beat` migrations (aplicadas no setup inicial)

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
- ⏳ `tests/integration/test_rls.py` — **40 testes RLS verdes** (8 fundação + 24 Onda 1 + 4 Agendamento + 8 Onda 3 + 4 Onda 4). Cobertura completa do item 7.
- ⏳ `tests/integration/test_tasks.py` — **3 testes Celery verdes** rodando com `CELERY_TASK_ALWAYS_EAGER`: eco MVP (`process_inbound_message` cria saída + Outbox), `send_outbox` marca como `enviado`, `send_outbox` é idempotente quando linha já não está `pendente`.
- ⏳ `tests/integration/test_api.py` — **5 testes verdes** dos health endpoints: `/ready` 200, `/health` 200 com todas dependências, `/health` 503 quando Celery sem workers, `/health` 503 quando Redis falha, garantia de que `/api/health` é público (não exige `X-Clinic-Slug`).
- ❌ `tests/integration/test_webhook_idempotency.py`
- ❌ `tests/integration/test_evolution_provider.py`
- ❌ `tests/fixtures/evolution_webhooks/` com payloads reais

### 13. Verificação end-to-end
- ✅ `make up` em <5min em máquina nova — stack sobe limpo: 7/7 containers UP (postgres, redis, langfuse-db, langfuse, web, worker, beat) com worker descobrindo automaticamente as 2 tasks via autodiscover.
- ✅ `make test` ≥ 30 testes verdes (≥ 10 RLS) — **48/48 verdes hoje** (40 RLS + 3 Celery + 5 API); critério atingido com folga
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

1. **`POST /api/webhooks/whatsapp/{canal_id}`** (item 8 final) — fecha o loop do MVP: valida HMAC com `webhook_secret` de `ClinicaCanal`, dedup pela unique parcial em mensagens, dispatcha `process_inbound_message.delay(...)`. Eco volta pelo `send_outbox`.
2. **EvolutionProvider** (item 10) — HTTP client real (httpx) para substituir o stub `_entrega_via_provider_stub` em `send_outbox`.
3. **Langfuse client + primeiro trace** (item 11) em `apps.observability`.
4. **ADRs faltantes**: 0001 (Django vs n8n) e 0003 (Anthropic + OpenRouter) para fechar o trio fundacional.
5. **Hardening: trocar `DATABASE_URL` para `app_readwrite`** em produção (item 13 último marcador) — habilita RLS de verdade em runtime, hoje ela só aplica nos testes via `SET LOCAL ROLE`.

Critério para encerrar a Fase 1 (todos os 10 pontos do plano em
[`../plans/01-fundacao-fase-1.md`](../plans/01-fundacao-fase-1.md)
seção "Critérios de conclusão"). Falta ainda webhook WhatsApp,
Evolution provider, Langfuse client, health endpoint, eco MVP e
testes E2E.
