---
name: evolution-api
type: integracao
tags: [whatsapp, mvp, canal]
---

# Evolution API

> Provedor WhatsApp do MVP. Recebe webhooks de mensagens dos pacientes e expõe API pra envio outbound. Vai ser substituído pela WhatsApp Cloud API (Meta) na fase de produção.

## Papel

Canal único de comunicação MedChat ↔ paciente no MVP. Toda conversa do produto passa por aqui:

- **Inbound:** paciente manda mensagem no WhatsApp → Evolution dispara webhook pro MedChat.
- **Outbound:** MedChat envia resposta → grava em `outbox` (regra do projeto) → Celery worker chama API da Evolution.

## Direção

- [x] Inbound — Evolution manda webhook pro MedChat
- [x] Outbound — MedChat chama API da Evolution

## Configuração por clínica

Cada clínica tem 1 linha em `ClinicaCanal` com `tipo = "whatsapp_evolution"`. Os dados ficam em `ClinicaCanal.config` (JSONB):

```json
{
  "instance_id": "<id da instância Evolution>",
  "token": "<token de auth da Evolution>"
}
```

`config` é JSONB porque Evolution e Cloud API têm shapes diferentes — JSON sem schema rígido permite trocar de provedor sem migration. Validação do shape fica na camada de aplicação.

Auth do webhook: HMAC do payload usando `ClinicaCanal.webhook_secret` (auto-gerado, 32 bytes base64url). Header esperado e algoritmo: a definir conforme docs Evolution.

## Endpoints / eventos importantes

| Endpoint / evento | Direção | Observações |
|---|---|---|
| `POST <medchat>/webhooks/evolution/<canal>` | inbound | Recebe `messages.upsert`. Valida HMAC com `webhook_secret`, dedup por `(canal_id, external_id)`. |
| `POST <evolution>/message/sendText/<instance>` | outbound | Envio de texto. Token da `ClinicaCanal.config` no header. |

## Idempotência

Toda mensagem inbound carrega `external_id` único do provedor. Constraint **parcial** em `mensagens`:

```sql
UNIQUE (canal_id, external_id) WHERE external_id IS NOT NULL
```

Se Evolution reenviar (timeout, retry), MedChat insere → conflito → retorna 200 sem reprocessar. O `WHERE external_id IS NOT NULL` é proposital: mensagens **geradas localmente** pelo bot (saídas) começam com `external_id=NULL` e coexistem livremente — só ganham unicidade depois que `send_outbox` confirma envio com o provedor e atribui o ID retornado.

Detalhes: [[conceitos-ai/idempotencia-via-unique-parcial]]. Regra do projeto: [`CLAUDE.md`](../../CLAUDE.md) §3.

Lado outbound: idempotência fica em outbox. Cada linha tem ID local; se o worker fizer retry, marca o mesmo outbox como sent — não duplica envio. Detalhes: [[conceitos-ai/outbox-pattern]].

## Outbox / send

- [x] Envio passa por `outbox` + Celery — **regra obrigatória** ([`CLAUDE.md`](../../CLAUDE.md) §4)
- [ ] ~~Envio síncrono no request~~

Motivo: Evolution pode estar fora do ar, lenta, ou rate-limitada. Sync no request quebra a UX e some com mensagens. Outbox + Celery dá retry automático com backoff e visibilidade.

## Gotchas

- **Evolution não tem garantia de entrega WhatsApp.** Status reais (entregue, lido) chegam por evento separado, podem demorar. Não confiar em "200 do POST sendText" como "mensagem chegou no paciente".
- **Janela de 24h do WhatsApp Business** vale aqui também — fora dela, só template aprovado funciona. Evolution não impede o envio mas a Meta bloqueia depois.
- **Reuso de instância**: uma instância Evolution = um número. Não confundir `instance_id` (Evolution) com `numero_e164` (campo do `ClinicaCanal`).
- **`webhook_secret` no header**: Evolution não tem padrão único de HMAC — verificar docs da versão usada antes de assumir o algoritmo.

## Migração futura

Quando: produção. Por quê: Evolution é não-oficial, depende de WhatsApp Web por baixo, frágil. Cloud API é oficial Meta.

A migração troca `tipo = whatsapp_evolution` por `tipo = whatsapp_cloud` na `ClinicaCanal` da clínica, e atualiza `config` com `phone_number_id` e `business_account_id` da Meta. Nenhum modelo de domínio precisa mudar — `config` é JSONB exatamente pra isso.

## Notas relacionadas

- [[entidades/clinica]] — `ClinicaCanal` armazena a config da Evolution
- [[fluxos/agendar-consulta]] — fluxo passa por aqui (inbound + outbound)

## Referências externas

- Docs Evolution API (versão usada — preencher quando definirmos a versão).
- [WhatsApp Cloud API (Meta)](https://developers.facebook.com/docs/whatsapp/cloud-api) — destino da migração futura.
