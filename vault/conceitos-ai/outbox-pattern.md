---
title: outbox-pattern
type: conceito-ai
tags: [outbox, celery, mensageria, integridade]
---

# Outbox pattern — desacoplar request HTTP de chamadas externas

> Em vez de `request → INSERT mensagem → POST WhatsApp → 200 OK`, fazemos `request → INSERT outbox → 200 OK em ms`, e Celery drena async com retry. Crash entre INSERT e POST não some com a mensagem.

## O que é

Padrão de integração descrito por Hohpe em *Enterprise Integration Patterns*. Quando uma operação **A** (gravar dado local) precisa disparar uma operação **B** (chamar API externa), em vez de fazer A+B dentro do mesmo request HTTP, A grava também numa tabela `outbox` e retorna; um worker assíncrono lê a outbox e executa B com retry.

## Por que usamos no MedChat

Toda mensagem que sai do MedChat em direção a um canal (WhatsApp via Evolution ou Cloud API, futuramente SMS/email) tem 4 problemas se for chamada direto do request:

1. **Latência acopla**: o paciente ou o webhook do provedor espera nossa request HTTP terminar; chamar uma API externa de dentro adiciona segundos.
2. **Crash entre "decidir resposta" e "enviar"** = paciente "respondeu" mas nunca recebeu. A mensagem foi gravada em `mensagens` mas o POST nunca aconteceu.
3. **Retry com backoff exponencial fica complicado** se a lógica vive no request handler — precisa logic de "se falhou, retentar em N segundos" no app, sem suporte de fila.
4. **Inspeção operacional**: o que tá emperrado pra enviar? Sem outbox, é mistério; com outbox, `SELECT * FROM outbox WHERE status='pendente'` mostra.

Alternativas descartadas:

- **Chamar a API direto do request**: testado e rejeitado pela regra `CLAUDE.md` §4 (outbox obrigatório pra envio externo).
- **Fila externa (RabbitMQ/Kafka)**: overkill agora. Postgres + Celery + Redis já dão `at-least-once` e retry exponencial.

## Como aparece no código

Tabela `outbox` em `apps/channels/models.py`:

```python
class Outbox(TenantAwareModel):
    class Tipo(models.TextChoices):
        WHATSAPP_TEXT = "whatsapp_text", ...
        WHATSAPP_TEMPLATE = "whatsapp_template", ...
        WHATSAPP_MEDIA = "whatsapp_media", ...

    class Status(models.TextChoices):
        PENDENTE = "pendente", ...
        ENVIADO = "enviado", ...
        FALHA = "falha", ...
        DESCARTADO = "descartado", ...

    tipo = models.CharField(max_length=24, choices=Tipo.choices)
    payload = models.JSONField(...)  # destino, corpo, template, media URL
    status = models.CharField(default=Status.PENDENTE)
    tentativas = models.PositiveIntegerField(default=0)
    proxima_em = models.DateTimeField(...)  # quando tentar de novo (backoff)
    enviado_em = models.DateTimeField(null=True)
    erro_ultimo = models.TextField(null=True)
```

Fluxo de **envio**:

```
request handler
  ↓
INSERT INTO outbox (tipo, payload, status='pendente', proxima_em=NOW())
  ↓
return 200 (em ms)

(em paralelo, Celery)
send_outbox task
  ↓
SELECT * FROM outbox
  WHERE status='pendente' AND proxima_em <= NOW()
  ORDER BY proxima_em
  LIMIT N
  ↓
para cada item: POST <provedor>
  ├─ sucesso: UPDATE status='enviado', enviado_em=NOW(); UPDATE mensagens SET external_id=<retornado>
  └─ falha: UPDATE status='falha', tentativas++, proxima_em = NOW() + 2^tentativas seg, erro_ultimo=...
```

`payload` carrega `mensagem_id` da `Mensagem` correspondente (gerada localmente com `external_id=NULL`); quando o envio retorna o ID do provedor, atualiza a `Mensagem`.

## Modelo / SDK / biblioteca usada

- **Tabela**: `outbox` (Postgres) — `apps/channels/models.py`.
- **Worker**: Celery + Celery Beat (Beat agenda a task `send_outbox` periodicamente).
- **Configuração**: `config/celery.py` (item 9 da Fase 1, ainda pendente).

## Gotchas

- **Outbox é at-least-once, não exactly-once**. Se o POST chega no provedor mas a resposta se perde, próxima execução repete o envio. **Solução: idempotência do lado do provedor** — Evolution e Cloud API geralmente aceitam um `client_id` e desduplicam.
- **Backoff exponencial precisa de teto.** Sem teto, item travado fica retentando pra sempre. Implementar: depois de N tentativas (ex.: 6 = ~1min, 2min, 4min... 32min total), marcar `descartado` e alertar.
- **Atomicidade da inserção**: o INSERT na outbox precisa fazer parte da MESMA transação que insere `mensagens` (saída local). Se uma fizer rollback, a outra não pode ficar. Por isso `INSERT outbox` é feito dentro do mesmo `with transaction.atomic()` do request handler.
- **Tasks Celery precisam de `app.clinica_id` setado** (porque `outbox` é tenant-owned via RLS). Decorator `@with_tenant` cuida disso.

## Notas relacionadas

- [[entidades/outbox]] — schema completo
- [[entidades/conversations]] — `Mensagem.external_id` é atualizada pelo `send_outbox` após envio
- [[integracoes/evolution-api]] — primeiro consumidor da outbox
- [[conceitos-ai/idempotencia-via-unique-parcial]] — outro pilar de robustez do envio

## Deep dive

- (a criar) `docs/ai-engineering/<NN>-outbox-pattern.md` — pedagogia longa quando o `send_outbox` task ganhar código.

## Referências externas

- [Outbox pattern (Hohpe / EIP)](https://www.enterpriseintegrationpatterns.com/patterns/messaging/MessagingMapper.html) — versão original
- [Microservices.io: Transactional outbox](https://microservices.io/patterns/data/transactional-outbox.html)
- [Celery docs](https://docs.celeryq.dev/) — fila e retry
