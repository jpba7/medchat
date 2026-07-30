# MedChat

SaaS B2B de secretária virtual com IA para clínicas médicas. Multi-tenant, WhatsApp como canal primário, agendamento + lembretes + handoff humano. Construído em Django + Postgres com observabilidade AI (Langfuse) e isolamento por Row-Level Security.

## Status

**Fase 1 — Fundação** (em andamento). Plano em [`docs/plans/01-fundacao-fase-1.md`](docs/plans/01-fundacao-fase-1.md).

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.13 com `uv` |
| Web | Django 5 + Django Ninja |
| Banco | Postgres 17 + pgvector (RLS multi-tenant) |
| Cache/broker | Redis 7 |
| Async | Celery + Celery Beat |
| LLM | Anthropic SDK (principal) + OpenRouter (fallback) |
| Obs AI | Langfuse self-hosted |
| Canal WhatsApp | Evolution API (MVP) → WhatsApp Cloud API (produção) |
| Deploy | Railway |

## Documentação

- [`docs/context/`](docs/context/) — produto, stack, decisões, histórico
- [`docs/adr/`](docs/adr/) — Architecture Decision Records
- [`docs/ai-engineering/`](docs/ai-engineering/) — notas pedagógicas de AI Engineering
- [`docs/plans/`](docs/plans/) — planos por fase

## Setup local

> ⚠️ Em construção. Fase 1 ainda não terminou. Quando terminar:
> ```bash
> docker compose up -d
> make migrate
> make createsuperuser
> make test
> ```

## Histórico

Este projeto começou como prova-de-conceito em n8n no repositório `n8n-automations` (workflow na instância Cloudfy). A revisão concluiu que Django+Postgres é a stack certa para o produto que estamos construindo (tenho familiaridade, multi-tenant SaaS regulado, com observabilidade e testes). A pasta n8n original ficou intocada como referência histórica — ver [`docs/context/04-historico-n8n.md`](docs/context/04-historico-n8n.md).
