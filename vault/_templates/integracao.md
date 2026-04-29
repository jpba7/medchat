---
name: template-integracao
type: integracao
tags: []
---

# {Nome da Integração}

> Frase única: o que essa integração faz pelo MedChat.

## Papel

Em qual ponto do produto essa integração aparece. 1-3 linhas.

## Direção

- [ ] Inbound — provedor manda webhook pro MedChat
- [ ] Outbound — MedChat chama API do provedor
- [ ] Ambos

## Configuração por clínica

- Onde mora: {ex.: `ClinicaCanal.config` JSONB}
- Campos relevantes: `<campo1>`, `<campo2>`
- Auth: {ex.: HMAC com `webhook_secret`, OAuth, API key}

## Endpoints / eventos importantes

| Endpoint / evento | Direção | Observações |
|---|---|---|
| `<endpoint>` | inbound/outbound | {comentário curto} |

## Idempotência

- Como o MedChat dedup: {ex.: `(canal_id, external_id)` unique}
- O que pode causar duplicata vinda do provedor.

## Outbox / send

- [ ] Envio passa por `outbox` + Celery (regra do projeto)
- [ ] Envio síncrono no request (justificar)

## Gotchas

- {armadilha conhecida}

## Migração futura

- {ex.: Evolution → Cloud API quando? Por quê?}

## Notas relacionadas

- `[[entidades/<entidade-que-armazena-config>]]`
- `[[fluxos/<fluxo-que-usa>]]`

## Referências externas

- {docs oficiais do provedor}
