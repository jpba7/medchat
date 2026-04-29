---
name: outbox
type: entidade
tags: [tenant-aware, outbox, evento-bot, observabilidade, celery]
---

# `Outbox` (em `apps/channels`) e `EventoBot` (em `apps/observability`)

> Fila de envio externo + log operacional. `Outbox` é o "armazém" de mensagens pendentes pra canal externo (WhatsApp); `EventoBot` é o registro estruturado de fatos relevantes da operação. Implementam, juntas, o item 7 fechado da Fase 1.

## Papel

### `Outbox`

Toda mensagem que sai do MedChat em direção a um canal externo passa por aqui antes de virar request HTTP. Permite que Celery consuma em background, com retry exponencial e visibilidade operacional.

Regra do projeto ([`CLAUDE.md`](../../CLAUDE.md) §4): **nunca chamar Evolution/Cloud API direto do request — gravar em outbox e deixar Celery enviar.**

### `EventoBot`

Log estruturado de fatos da operação que importam pra painel/auditoria. Complementa o Langfuse (que tem trace de prompt/response detalhado) com um view local: o painel da clínica consegue mostrar "o que aconteceu nessa conversa" sem depender do Langfuse estar online.

## Onde mora no código

| Modelo | App | Path |
|---|---|---|
| `Outbox` | `channels` | [`apps/channels/models.py`](../../apps/channels/models.py) |
| `EventoBot` | `observability` | [`apps/observability/models.py`](../../apps/observability/models.py) |

Ambos no commit `00f3287`. Tabelas: `outbox`, `eventos_bot`.

## Tenant-aware?

| Modelo | Tenant-owned? |
|---|---|
| `Outbox` | Sim — `clinica_id` direto |
| `EventoBot` | Sim — `clinica_id` direto |

## Campos — `Outbox`

| Campo | Tipo | Por quê existe |
|---|---|---|
| `tipo` | TextChoices | `whatsapp_text`, `whatsapp_template`, `whatsapp_media`. Determina shape do `payload`. |
| `payload` | JSONB | Dados específicos do tipo: destino, corpo, template_name+params, media URL. Inclui `mensagem_id` quando há linha em `mensagens` pra atualizar com o `external_id` retornado pelo provedor. |
| `status` | TextChoices, indexed | `pendente` (default), `enviado`, `falha` (com retry), `descartado` (sem retry). |
| `tentativas` | PositiveInt(default=0) | Quantas vezes a task tentou. |
| `proxima_em` | DateTimeField, indexed | Quando a task pode tentar de novo. **Backoff exponencial sobe esse valor a cada falha.** |
| `enviado_em` | DateTimeField, nullable | Timestamp do envio bem-sucedido. |
| `erro_ultimo` | TextField, nullable | Mensagem do último erro do provedor (debug operacional). |

Index principal: `(clinica, status, proxima_em)` — drive a query do consumidor `send_outbox`.

### Shapes do `payload` por `tipo`

```
whatsapp_text:     {to_e164, body, mensagem_id?}
whatsapp_template: {to_e164, template_name, params, mensagem_id?}
whatsapp_media:    {to_e164, media_url, caption, mensagem_id?}
```

`mensagem_id` é opcional — quando o consumidor envia, atualiza a `Mensagem` com o `external_id` retornado pelo provedor.

## Campos — `EventoBot`

| Campo | Tipo | Por quê existe |
|---|---|---|
| `conversa` | FK Conversa, **SET_NULL**, **nullable** | Eventos globais (ex.: erro de health check, falha de provedor que afeta clínica toda) não pertencem a conversa. SET_NULL preserva auditoria mesmo se a conversa for deletada. |
| `tipo_evento` | TextChoices | `mensagem_recebida`, `resposta_enviada`, `tool_call`, `erro`, `transicao_status`. |
| `dados` | JSONB | Conteúdo variável por tipo. |

### Shapes do `dados` por `tipo_evento`

```
mensagem_recebida: {external_id, conteudo}      ← resumo do que chegou
resposta_enviada:  {external_id, latencia_ms}
tool_call:         {nome, argumentos, resultado}
erro:              {stack_trace, exception_type, contexto}
transicao_status:  {de, para}                   ← Conversa.status mudou
```

Indexes:
- `(clinica, -criado_em)` — query principal "últimos eventos de uma clínica".
- `(conversa, -criado_em)` parcial (`WHERE conversa IS NOT NULL`) — histórico desta conversa.

## Relacionamentos

- `Clinica` ← FK ← `Outbox`, `EventoBot`
- `Conversa` ← FK (SET_NULL) ← `EventoBot`
- `Outbox` ↔ `Mensagem` por `payload.mensagem_id` (link "lógico", não FK formal)

## Regras / invariantes

- **`Outbox.proxima_em` controla quando a task pode pegar.** Sem ela, sem backoff. Sem teto de tentativas, item travado fica retentando pra sempre — implementar teto na lógica do `send_outbox`.
- **`Outbox` e `Mensagem` precisam ser inseridos na MESMA transação.** Se uma fizer rollback, a outra não pode ficar — caso contrário a `Mensagem` existe sem `Outbox` (não vai ser enviada) ou vice-versa.
- **`EventoBot` é fire-and-forget.** Falhas em criar evento não devem abortar o request principal — log do tipo "interessante mas não crítico".
- **`SET_NULL` em `EventoBot.conversa`** preserva histórico se a conversa for deletada. Importante pra auditoria.

## Gotchas

- **`Outbox` é at-least-once, não exactly-once.** Se POST chega no provedor mas a resposta se perde, próxima execução repete. Idempotência fica do lado do provedor (Evolution e Cloud aceitam `client_id`).
- **`EventoBot` ≠ `logging` Python.** Eventos aqui vão pro painel da clínica. Logs de aplicação (debug, traceback completo) vão pelo `logging` padrão e Sentry.
- **`payload` e `dados` JSONB sem schema rígido.** Validação de shape fica na camada que escreve. Se mudar shape, código antigo lendo pode quebrar — nunca remover chave; só adicionar.
- **`erro_ultimo` é texto livre do provedor.** Pode ter dados sensíveis se o provedor retornar payload do paciente em erro (raro mas possível). Truncar ou sanitizar antes de armazenar pro caso.
- **Tasks Celery precisam de `app.clinica_id` setado** (RLS). Decorator `@with_tenant` cuida — sem ele, RLS bloqueia leitura.

## Notas relacionadas

- [[entidades/clinica]] — tenant root
- [[entidades/conversations]] — `Mensagem.external_id` é atualizada pelo `send_outbox` após envio
- [[conceitos-ai/outbox-pattern]] — explicação detalhada do pattern
- [[integracoes/evolution-api]] — primeiro consumidor da `Outbox`
- [[aprendizados/medchat-superuser-bypassrls]] — RLS aqui também é silenciada com SUPERUSER

## Referências externas

- [Outbox pattern](https://microservices.io/patterns/data/transactional-outbox.html)
- [Langfuse](https://langfuse.com/) — observabilidade AI complementar
- [Celery + Beat](https://docs.celeryq.dev/) — fila e scheduler periódico
