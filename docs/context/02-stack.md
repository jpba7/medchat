---
name: Stack MedChat
description: Stack técnica decidida para o MedChat (n8n, LLM, DB, canais WhatsApp, painel).
type: project
originSessionId: 75279bca-61cb-467e-9eb0-e13093a19b81
---
**Stack decidida (2026-04-17):**
- n8n hospedado em Cloudfy (`https://unknownserval-n8n.cloudfy.live`) — modular, sub-workflows por responsabilidade
- LLM: OpenRouter (mantido; permite trocar modelo sem refatorar)
- Supabase: dados da aplicação — redesenho do zero (tabelas antigas `cadastro` e `interno` são descartáveis). Schema multi-tenant por `clinica_id`
- Postgres (via LangChain memoryPostgresChat): histórico de conversas
- Redis: debounce de mensagens, flags de bloqueio de IA, chaves temporárias
- Canais WhatsApp: Evolution API no MVP; WhatsApp Cloud API (Meta oficial) em produção — evita banimentos. Código deve abstrair o canal
- Painel: Django (outro projeto). O n8n expõe schemas Supabase + webhooks para o Django consumir
- Calendário: adapter pattern — Supabase interno OU Google Calendar / Outlook / Apple (cliente escolhe por clínica)

**Why:** Evolution é frágil em produção (risco de ban). Django é o backend do painel, então o schema Supabase precisa ser pensado para ser consumido por ORM Python (Django). OpenRouter foi escolhido pela flexibilidade mesmo com desvantagens de caching.

**How to apply:** Todo novo workflow deve ler/gravar via `clinica_id`, não hardcodar `evolution_account_name`. Tabelas do Supabase devem ter FK clara para `clinicas` e convenções de snake_case (Django-friendly). Ao integrar calendário, usar camada de adapter (função n8n ou sub-workflow) em vez de Google Calendar node direto.
