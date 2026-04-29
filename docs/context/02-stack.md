---
name: Stack MedChat
description: Stack técnica do MedChat após migração do POC n8n+Supabase para Django+Postgres na Fase 1.
type: project
originSessionId: 75279bca-61cb-467e-9eb0-e13093a19b81
ultima_atualizacao: 2026-04-29
---

**Decisão original (2026-04-17):** o POC do MedChat foi montado em n8n hospedado na Cloudfy, com Supabase como banco e OpenRouter como LLM. Funcionava como prova-de-conceito mas não escalava para produto: testes inviáveis, lógica de tenant espalhada por nodes, segredos misturados com config.

**Migração (2026-04-27 em diante):** rasgamos o n8n e refizemos a fundação em Django+Postgres. O n8n original ficou em `C:\Users\peedr\n8n-automations\` (workflow `0O13PjgBKcONHd0F`) como referência histórica, intocado. Detalhes da decisão em `docs/adr/0002-rls-vs-schema.md`.

**Stack atual (Fase 1 fechada — imutável durante a Fase 2):**

| Camada | Escolha | Justificativa breve |
|---|---|---|
| Linguagem | Python 3.13 + `uv` | `uv` resolve dependências em segundos; CPython 3.13 é estável e largamente suportado |
| Framework web | Django 6 + Django Ninja | ORM maduro com migrations versionadas; Ninja entrega REST tipado sem o peso do DRF |
| Banco | Postgres 17 com `pgvector` | RLS nativo (peça central da multi-tenancy), `tstzrange` + `btree_gist` para anti-overlap em agendamentos, JSONB para policies/payload, pgvector pronto para retrieval da Fase 2 |
| Cache + broker | Redis 7 | Cache de app, broker do Celery, estado transitório de conversa |
| Async | Celery 5 + Celery Beat (django-celery-beat) | `autodiscover_tasks` por app, retry exponencial, scheduler em DB |
| API HTTP | Django Ninja | Endpoints `/api/health`, `/api/ready`, `/api/webhooks/whatsapp/{canal_id}` |
| LLM | Anthropic SDK (principal) + OpenRouter (fallback) | Anthropic com prompt caching forte; OpenRouter cobre indisponibilidade. Não há chamada real ainda — entra na Fase 2 |
| Observabilidade AI | Langfuse self-hosted | Container próprio no `docker-compose.yml`; primeiro trace na Fase 1 item 11 |
| Canal WhatsApp | Evolution API (MVP) → WhatsApp Cloud API (produção) | Evolution rápido para protótipo; Cloud para evitar bans em produção. Adapter `WhatsAppProvider` (Fase 1 item 10) abstrai o canal |
| Deploy | Railway | PaaS simples para fase de validação; Dockerfile compatível |
| Testes | pytest + pytest-django + factory-boy | Integração contra Postgres real; RLS isolation testado por tabela |
| Lint / format | ruff | Único formatter+linter; rápido |
| Vault de conhecimento | Obsidian markdown em `vault/` | Notas atômicas (entidades, fluxos, conceitos AI). Versionadas no Git |

**O que mudou em relação ao POC:**

- **Banco**: saímos de Supabase (Postgres gerenciado) para Postgres 17 self-hosted. Permite controle fino sobre RLS, extensions (`btree_gist`, `pgvector`) e roles (`app_readwrite`/`app_jobs`).
- **Multi-tenancy**: o POC dependia de `WHERE clinica_id = ?` em cada workflow node. Hoje é Row-Level Security do Postgres + `RLSMiddleware` Django + `TenantAwareModel.save()` validando — defesa em 4 camadas.
- **Orquestração**: n8n trocou por Celery + Postgres. Tasks Python testáveis com pytest, retry exponencial declarativo, idempotência via `task_id`.
- **Painel administrativo**: ficou Django (mesmo projeto) em vez de outro projeto separado. O painel reusa os modelos e o admin do Django.

**Por que sair de OpenRouter como principal**: quando entrarmos na Fase 2, queremos prompt caching agressivo da Anthropic (Claude Sonnet) — desconto de até 90% nos tokens de input quando há prefixo estável. OpenRouter cobre LLMs como fallback (indisponibilidade) e para testar modelos diferentes sem refatorar, mas o cache fica imbatível direto no provedor.

**Como aplicar:**

- Toda nova feature lê/grava via `clinica_id` (multi-tenant).
- Modelos tenant-aware herdam `TenantAwareModel` (`apps/core/models.py`).
- Toda migration de tabela tenant-aware chama `apply_rls_policy('<tabela>')` (`apps/core/migrations/0002_grants_app_roles.py`).
- Tasks Celery com lógica de tenant usam `@with_tenant` decorator (`apps/core/tenancy.py`).
- Envio externo (WhatsApp, futuro SMS/email) **sempre** via `Outbox` + `send_outbox` task — nunca chamar API direto do request.
- Snake_case e nomes de domínio em pt-BR (`agendamento`, `medico`, `paciente`).
