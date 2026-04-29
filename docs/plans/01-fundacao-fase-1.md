# Plano — MedChat Fase 1 (Fundação Django)

## Context

O projeto atual no diretório `C:\Users\peedr\n8n-automations` é um experimento em n8n (workflow `0O13PjgBKcONHd0F`) que misturava um bot comercial B2B com a ideia de secretária virtual para clínicas — dois produtos diferentes num workflow monolítico sandbox. Após revisão conjunta, decidimos:

1. **Rasgar o workflow n8n e repensar o produto.** MedChat passa a ser um SaaS B2B multi-tenant de secretária virtual IA: clínicas contratam, pacientes conversam via WhatsApp.
2. **Migrar de n8n+Supabase para Django+Postgres.** Claude Code opera num codebase Python infinitamente melhor do que sobre JSON de workflow; o painel já seria Django, então o produto inteiro consolida no mesmo stack; testes, multi-tenancy e observabilidade ficam muito superiores.
3. **Construir aprendendo AI Engineering.** O usuário é iniciante em AI Eng e mira empregabilidade. Cada feature AI vem com um `.md` pedagógico em `docs/ai-engineering/` antes de ser implementada.

Esta Fase 1 é a fundação: stack de dev local no ar, modelo multi-tenant com isolamento por Row-Level Security do Postgres, webhook de WhatsApp entrando via Evolution API, tarefas async com Celery, observabilidade AI com Langfuse self-hosted desde o início. Sem LLM agente nessa fase — só eco de teste. Fases 2+ constroem o agente, handoff, lembretes e Google Calendar em cima.

Resultado esperado: repositório pronto para construir o agente AI com confiança arquitetural, e uma pasta de aprendizado que serve de portfólio.

---

## Decisões de stack (imutáveis nesta fase)

| Camada | Escolha | Nota |
|---|---|---|
| Linguagem/gerenciador | Python 3.13 + `uv` | `uv init`, `uv add`, `uv run` |
| Framework web | Django 6.x + Django Ninja | Ninja = API tipada estilo FastAPI |
| Banco | Postgres 17 com `pgvector` | Multi-tenant via RLS (`SET LOCAL app.clinica_id`) |
| Cache/broker | Redis 7 | Celery broker + cache de app |
| Async | Celery + Celery Beat (django-celery-beat) | Jobs + cron de lembretes |
| LLM | Anthropic SDK principal + OpenRouter fallback | Nesta fase ainda não há chamada de LLM |
| Observabilidade AI | Langfuse self-hosted | Container próprio no docker-compose |
| Canal WhatsApp | Evolution API (MVP) / Cloud API (Fase 6) | Adapter pattern `WhatsAppProvider` |
| Deploy | Railway | Dockerfile compatível |
| Testes | pytest + pytest-django + pytest-asyncio + factory-boy | RLS isolation test obrigatório |
| Lint | ruff | CI + pre-commit |
| Aprendizado | `docs/ai-engineering/*.md` | Um por conceito AI, antes de usar |

---

## Estrutura do repositório

```
n8n-automations/                       # repo raiz
├── workflows/                         # n8n legado (referência histórica, não tocar)
├── CLAUDE.md                          # atualizar com nova stack
├── docs/
│   ├── ai-engineering/                # notas pedagógicas (Seção "Aprendizado")
│   └── adr/                           # Architecture Decision Records (ADR-001…)
├── medchat/                           # projeto Django raiz
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .python-version                # 3.13
│   ├── .env.example
│   ├── manage.py
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.override.yml    # gitignored — overrides locais
│   ├── Makefile                       # make up / make test / make shell
│   ├── pytest.ini
│   ├── conftest.py                    # fixtures tenant / RLS
│   ├── config/
│   │   ├── settings/{base,dev,prod,test}.py
│   │   ├── urls.py
│   │   ├── api.py                     # NinjaAPI raiz agregando routers
│   │   ├── celery.py
│   │   └── asgi.py
│   ├── apps/
│   │   ├── core/                      # TenantAwareModel, RLSMiddleware, with_tenant
│   │   ├── clinics/                   # Clinica, ClinicaCanal, ClinicaPolitica
│   │   ├── patients/                  # Paciente
│   │   ├── catalog/                   # Especialidade, Medico, Convenio, Disponibilidade
│   │   ├── appointments/              # Agendamento + exclusion constraint
│   │   ├── conversations/             # Conversa, Mensagem, Handoff
│   │   ├── bot/                       # Fase 2+ (scaffolding só)
│   │   ├── channels/                  # adapters WhatsApp (Evolution / Cloud)
│   │   └── observability/             # Langfuse client, health, metrics
│   └── tests/{integration,e2e}/
```

**Por que esses apps (e não outros):**
- `core` existe separado de `clinics` porque o mixin de multi-tenancy e o middleware não pertencem ao domínio clínica — evita import cycle.
- `catalog` existe separado de `clinics` porque especialidade/médico/convênio são entidades grandes que ganharão CRUD no painel. Não inchar `clinics`.
- `bot` separado de `conversations`: `conversations` é persistência; `bot` é inteligência (Anthropic, Langfuse, prompts). Separação DDD clara.
- `channels` isolado porque cada provider tem payload/auth/rate-limit próprios. Adapter pattern só fica testável se isolado.

---

## Schema Postgres (Fase 1)

Todas as tabelas tenant-owned têm `clinica_id UUID NOT NULL` + índice + política RLS. PKs são `UUID v7` (evita leakage de contagem entre tenants).

### Globais (sem RLS)
- `clinicas` — raiz do tenant (`id`, `nome`, `slug`, `cnpj`, `timezone`, `horario_comercial JSONB`, `ativa`)

### Tenant-owned (RLS obrigatório)
- `clinica_canais` — (`clinica_id`, `tipo` enum `whatsapp_evolution|whatsapp_cloud`, `config JSONB` com credenciais criptografadas, `numero_e164`, `webhook_secret`, `ativo`). Unique `(clinica_id, tipo)` no MVP.
- `clinica_politicas` — (`clinica_id`, `chave`, `valor JSONB`). Chaves MVP: `cancelamento_antecedencia_h`, `remarcacao_max_vezes`, `cpf_obrigatorio`, `lgpd_texto`, `saudacao_bot`, `handoff_numero_atendente`, `lembrete_janelas_h`, `horario_handoff_humano`.
- `pacientes` — (`clinica_id`, `telefone_e164`, `nome`, `cpf NULLABLE`, `lgpd_aceito_em`, `metadata JSONB`). Unique `(clinica_id, telefone_e164)`.
- `especialidades` — (`clinica_id`, `nome`, `ativo`).
- `medicos` — (`clinica_id`, `nome`, `crm`, `especialidade_id FK`, `duracao_consulta_min`, `ativo`).
- `convenios` — (`clinica_id`, `nome`, `ativo`).
- `medico_convenios` — M2M (`medico_id`, `convenio_id`).
- `medico_disponibilidades` — (`medico_id`, `dia_semana`, `inicio`, `fim`). Fonte de slots MVP.
- `agendamentos` — (`clinica_id`, `paciente_id`, `medico_id`, `convenio_id`, `inicio_em`, `fim_em`, `status`, `origem` enum `bot|humano|import`, `external_event_id NULLABLE`, `external_provider NULLABLE`). **Exclusion constraint `btree_gist` impedindo overlap por médico.**
- `conversas` — (`clinica_id`, `paciente_id`, `canal_id`, `status` enum `bot|handoff_aguardando|handoff_ativo|encerrada`, `contexto JSONB`).
- `mensagens` — (`clinica_id`, `conversa_id`, `direcao`, `remetente`, `conteudo`, `payload_raw JSONB`, `external_id`). **Unique `(canal_id, external_id)` — idempotência.**
- `handoffs` — (`clinica_id`, `conversa_id`, `gatilho`, `aberto_em`, `aceito_por`, `encerrado_em`, `resolucao`).
- `eventos_bot` — trace local leve (complementa Langfuse; útil pra painel).
- `outbox` — (`clinica_id`, `tipo`, `payload JSONB`, `status`, `tentativas`, `proxima_em`). **Outbox pattern** para envio de WhatsApp resiliente.

Todas as tabelas têm `id`, `criado_em`, `atualizado_em`, `deletado_em NULLABLE` (soft delete onde faz sentido).

---

## Multi-tenancy por Row-Level Security

**Mecanismo:**
1. Middleware `apps.core.middleware.RLSMiddleware` resolve `clinica_id` a partir do request — header `X-Clinic-Slug` (painel futuro) ou `webhook_secret` (canal). Abre `transaction.atomic()` e executa `SET LOCAL app.clinica_id = '<uuid>'`. Sem isso o middleware aborta com 500 fail-loud.
2. Policies padrão em cada tabela tenant-owned:
   ```sql
   CREATE POLICY tenant_isolation ON pacientes
     USING (clinica_id = current_setting('app.clinica_id')::uuid);
   ```
3. Role `app_readwrite` normal usa policies; role `app_jobs` tem `BYPASSRLS` explícito para tasks cross-tenant (lembretes diários varrendo todas clínicas).
4. `TenantAwareModel` abstract: FK `clinica` + save() valida que `current_setting('app.clinica_id')` bate com `self.clinica_id` (cinto e suspensório).
5. Celery: decorator `@with_tenant(clinica_id)` abre transação, seta `app.clinica_id`, limpa ao fim. Lint custom no CI rejeita task tenant-aware sem esse decorator.

**Biblioteca base:** `django-pgtrigger` para triggers custom (ex.: proibir `UPDATE clinica_id` em qualquer linha). RLS puro via `RunSQL` nas migrations.

**Teste anti-vazamento obrigatório:** `tests/integration/test_rls.py` cria 2 clínicas com dados idênticos, alterna `SET app.clinica_id` entre elas, asserta isolamento em cada model tenant-owned. Mínimo 1 caso por tabela.

---

## Abstração de canal WhatsApp

**Interface única** em `apps/channels/providers/base.py`:
```python
class WhatsAppProvider(Protocol):
    async def send_text(
        self, to_e164: str, body: str, conversation_ref: str
    ) -> ProviderMessageId: ...
    def parse_webhook(
        self, raw: dict, signature: str
    ) -> list[InboundMessage]: ...
    def verify_signature(
        self, raw_body: bytes, signature: str, secret: str
    ) -> bool: ...
```

Dataclasses `InboundMessage` e `ProviderMessageId` no mesmo módulo — contrato fechado.

**Fase 1 entrega:**
- `EvolutionProvider` completo (HTTP client + parser de webhook + HMAC).
- `CloudAPIProvider` stub que levanta `NotImplementedError`; testes marcados `@pytest.mark.phase6`.
- Factory `get_provider(canal: ClinicaCanal) -> WhatsAppProvider` lendo `canal.tipo`.

**Fase 6:** `CloudAPIProvider` completo + template messages do Meta + migração.

---

## Entry points HTTP (Ninja)

- `POST /api/webhooks/whatsapp/{canal_id}`
  1. Valida HMAC signature via provider.
  2. `parse_webhook` → lista de `InboundMessage`.
  3. Upsert `mensagens` usando `(canal_id, external_id)` — idempotência.
  4. Dispatch `process_inbound_message.delay(mensagem_id)`.
  5. Responde 200 em <500ms. **Nunca chama LLM no request.**
- `GET /api/health` — Postgres ping + Redis ping + Celery `inspect().ping`. Usado pelo Railway readiness.
- `GET /api/ready` — só Postgres (liveness separado).
- `POST /api/webhooks/langfuse` — stub pra Fase 3 (scores/annotations).

**Fluxo do Celery task `process_inbound_message` (Fase 1 mínimo):**
1. Abre `atomic()` + `with_tenant(clinica_id)`.
2. Resolve/cria `Paciente` (telefone → nome do pushName WhatsApp).
3. Atualiza/cria `Conversa`.
4. Grava resposta-eco `"Recebi. Em instantes respondo."` no `outbox`.
5. Task separada `send_outbox` consome FIFO por conversa.

LLM real entra na Fase 2.

---

## Docker Compose (dev local)

Serviços:
- `postgres` — `pgvector/pgvector:pg17`, volume `pgdata`, healthcheck `pg_isready`, port 5432
- `redis` — `redis:7-alpine`, appendonly, port 6379
- `langfuse-db` — Postgres 16 dedicado (Langfuse exige schema próprio; não misturar)
- `langfuse` — `langfuse/langfuse:3`, port 3000, envs `DATABASE_URL` (aponta langfuse-db), `NEXTAUTH_SECRET`, `SALT`
- `web` — build do Dockerfile, `uv run uvicorn config.asgi:application --reload`, bind ./medchat, port 8000
- `worker` — `uv run celery -A config worker -l info`
- `beat` — `uv run celery -A config beat -l info -S django`

Network: `medchat_net` (bridge). `.env.example` versionado; `.env` gitignored com `ANTHROPIC_API_KEY`, `LANGFUSE_PUBLIC_KEY/SECRET_KEY`, `EVOLUTION_BASE_URL/API_KEY`.

---

## Aprendizado AI Engineering — `docs/ai-engineering/`

Cada `.md` tem: frontmatter (`status: draft|em-uso`), **conceito** (2-3 parágrafos), **por que usamos no MedChat**, **como funciona** (código mínimo), **referências externas**. Criados antes/junto da feature — não depois.

Na Fase 1, criar os 7 fundacionais:

| # | Arquivo | Ementa |
|---|---|---|
| 01 | `01-por-que-nao-n8n.md` | Quando workflow visual quebra e por que SaaS regulado pede código |
| 02 | `02-primeira-chamada-anthropic.md` | SDK Anthropic, `messages.create`, streaming vs sync |
| 03 | `03-system-prompts-estruturados.md` | Ordem `system → tools → messages`, anti-patterns |
| 04 | `04-prompt-caching-anthropic.md` | `cache_control`, TTL 5min/1h, ordem importa |
| 05 | `05-tool-use-fundamentos.md` | JSON schema de tools, loop agentic, `stop_reason` |
| 06 | `06-observabilidade-langfuse.md` | Traces, spans, scores, por que self-hosted pra LGPD |
| 07 | `07-multi-tenant-rls-postgres.md` | Isolamento por DB; risco de vazamento silencioso |

ADRs em `docs/adr/` para decisões arquiteturais grandes (ADR-001: Django+Postgres vs n8n, ADR-002: RLS vs schema-per-tenant, ADR-003: Anthropic SDK + OpenRouter fallback).

---

## Passo-a-passo de execução

1. **Setup inicial** — `uv init medchat`, `uv python pin 3.13`, adicionar dependências principais (Django, Ninja, psycopg[binary,pool], redis, celery[redis], django-celery-beat, anthropic, openai, langfuse, django-pgtrigger, django-environ, pydantic, cryptography, httpx) + dev (pytest, pytest-django, pytest-asyncio, factory-boy, ruff, ipython).
2. **Django scaffold** — `django-admin startproject config medchat/`, settings modular (`base/dev/prod/test`), `django-environ` lendo `.env`.
3. **Criar apps** — `startapp` nos 9 apps listados na estrutura.
4. **Docker Compose + Dockerfile** — `python:3.13-slim` + uv; compose com os 7 serviços. `Makefile` com `up/down/logs/test/shell/migrate`.
5. **apps/core** — `TenantAwareModel`, `RLSMiddleware`, decorator `with_tenant`, `conftest.py` com fixtures `clinica_a/clinica_b` e `rls_set_tenant`.
6. **Migrations base** — `clinicas` → `clinica_canais` → `clinica_politicas`. Migration de data criando policies RLS via `RunSQL` e triggers pgtrigger.
7. **Migrations domínio** — `pacientes`, `catalog` (especialidades, medicos, convenios, disponibilidades), `appointments` (com exclusion constraint btree_gist), `conversations`, `mensagens`, `handoffs`, `outbox`, `eventos_bot`.
8. **Ninja API** — `/api/health`, `/api/ready`, `/api/webhooks/whatsapp/{canal_id}` (stub que valida signature + enfileira task). Montar no `config/api.py`.
9. **Celery** — `config/celery.py`, task `process_inbound_message` (eco MVP), task `send_outbox`. Django-celery-beat migrations.
10. **EvolutionProvider** — HTTP client httpx + parser webhook + HMAC verify. Testes unitários contra payloads reais (fixtures em `tests/fixtures/evolution_webhooks/`).
11. **Langfuse client** — singleton em `apps/observability/langfuse.py`. Primeiro trace manual no webhook. Docs `06-observabilidade-langfuse.md` + screenshots do Langfuse local.
12. **docs/ai-engineering** — criar os 7 `.md` + ADR-001/002/003. Atualizar `CLAUDE.md` raiz com a nova stack.

---

## Riscos e mitigações

| Risco | Por que dói | Mitigação |
|---|---|---|
| **RLS silencia erros** — middleware não setou `app.clinica_id`, queryset retorna vazio, parece bug de lógica | Bugs fantasma em produção; mascarar regressão até virar incidente | Policy fallback `USING (false)`; middleware aborta 500 se não resolver tenant; teste `test_rls_fails_without_tenant` |
| **Prompt caching posicional** — Anthropic cacheia do início até o marcador; ordem errada invalida cache inteiro | Custo 10x maior sem sinal claro | Docs `04-prompt-caching-anthropic.md` + asserção `_assert_cache_structure()` nos testes quando agent entrar |
| **Webhook não idempotente** — Evolution re-entrega em falha; sem unique, paciente recebe mensagem duplicada | UX ruim + incidente com cliente | Unique `(canal_id, external_id)` + task Celery `task_id=external_id` (dedup nativa) |
| **Celery + RLS vaza connection** — worker pega conexão do pool com `app.clinica_id` setado da task anterior | Vazamento cross-tenant silencioso | Decorator `@with_tenant` obriga `atomic()`; lint custom rejeita task tenant-aware sem decorator |
| **Evolution API instável** — provider third-party fora de controle | Downtime quebra MVP inteiro | Outbox pattern + retry exponencial + alerta em `handoffs` se outbox stuck |
| **Langfuse self-hosted = operação** — mais um Postgres, SALT/secrets, disco | Custo e overhead cognitivo; downgrade em incidente | Documentar em `06-observabilidade-langfuse.md`; manter como opcional em `dev.py` (ENV `LANGFUSE_ENABLED=false` pula tracing) |

---

## Critérios de conclusão da Fase 1

Declarar vitória quando, **simultaneamente**:

1. `make up` sobe stack completa em máquina nova em <5min, sem erros.
2. `pytest` verde com ≥30 testes, incluindo ≥10 de RLS isolation (1 por tabela tenant-owned).
3. Mensagem WhatsApp num número Evolution configurado → bot responde `"Recebi. Em instantes respondo."` em <10s.
4. Trace da mensagem aparece no Langfuse self-hosted local com metadados (`clinica_id`, `paciente_id`, `mensagem_id`).
5. 2ª clínica criada; `app.clinica_id=B` em queries de clínica A retorna 0 rows em todas as tabelas tenant-owned (teste automatizado verde).
6. `GET /api/health` → 200 com checks Postgres + Redis + Celery OK.
7. 7 arquivos em `docs/ai-engineering/` criados + 3 ADRs + `CLAUDE.md` raiz atualizado.
8. `docker build -f medchat/Dockerfile` + container boot com `.env` de prod simulado (sem exposição pública) funciona.
9. CI local (`make lint && make test`) verde.
10. Commit limpo em branch `main` (ou `foundation`, depois merge).

Só então avançamos pra **Fase 2** (router de intenções + primeiro agente Anthropic com tool use + persistência de contexto de conversa).

---

## Arquivos críticos a criar (Fase 1)

- `medchat/pyproject.toml`
- `medchat/docker-compose.yml`
- `medchat/Dockerfile`
- `medchat/Makefile`
- `medchat/.env.example`
- `medchat/config/settings/base.py`
- `medchat/config/api.py`
- `medchat/config/celery.py`
- `medchat/apps/core/models.py` (TenantAwareModel)
- `medchat/apps/core/middleware.py` (RLSMiddleware)
- `medchat/apps/core/tenancy.py` (with_tenant decorator)
- `medchat/apps/clinics/models.py`
- `medchat/apps/patients/models.py`
- `medchat/apps/catalog/models.py`
- `medchat/apps/appointments/models.py`
- `medchat/apps/conversations/models.py`
- `medchat/apps/channels/providers/base.py`
- `medchat/apps/channels/providers/evolution.py`
- `medchat/apps/channels/providers/cloud.py` (stub)
- `medchat/apps/channels/api.py` (webhook Ninja)
- `medchat/apps/observability/langfuse.py`
- `medchat/apps/observability/health.py`
- `medchat/conftest.py`
- `medchat/tests/integration/test_rls.py`
- `medchat/tests/integration/test_webhook_idempotency.py`
- `medchat/tests/integration/test_evolution_provider.py`
- `docs/ai-engineering/01-07*.md` (7 arquivos)
- `docs/adr/0001-django-vs-n8n.md`, `0002-rls-vs-schema.md`, `0003-anthropic-openrouter.md`
- `CLAUDE.md` (atualizar com nova stack na raiz)

---

## Verificação end-to-end

Checklist manual ao concluir:

```bash
# 1. Stack sobe limpa
cd medchat && make up
make migrate
make createsuperuser

# 2. Testes passam
make test                                 # >=30, >=10 RLS

# 3. Lint
make lint                                 # ruff check + format --check

# 4. Webhook local com Evolution mock (ou número real)
curl -X POST http://localhost:8000/api/webhooks/whatsapp/<canal_id> \
  -H "X-Signature: <hmac>" \
  -d @tests/fixtures/evolution_webhooks/text_message.json
# → 200 em <500ms, task Celery enfileirada, mensagem aparece no WhatsApp em <10s

# 5. Langfuse tem o trace
open http://localhost:3000                # login, conferir trace

# 6. Health
curl http://localhost:8000/api/health     # {"status":"ok","postgres":"ok","redis":"ok","celery":"ok"}

# 7. RLS isolation manual
psql ... -c "SET app.clinica_id = '<uuid-A>'; SELECT * FROM pacientes;"   # só da A
psql ... -c "SET app.clinica_id = '<uuid-B>'; SELECT * FROM pacientes;"   # só da B
psql ... -c "SELECT * FROM pacientes;"                                    # erro (sem tenant)

# 8. Docker build prod
docker build -f medchat/Dockerfile medchat/ -t medchat:fase1
docker run --env-file .env.prod.example medchat:fase1  # boot sem erro
```

Se todos os checks passam, Fase 1 está fechada e podemos iniciar Fase 2.
