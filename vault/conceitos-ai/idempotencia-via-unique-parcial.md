---
name: idempotencia-via-unique-parcial
type: conceito-ai
tags: [postgres, idempotencia, webhook, unique-parcial]
---

# Idempotência via `UNIQUE ... WHERE` parcial — dedup de webhook no banco

> Webhooks de WhatsApp são at-least-once: o provedor reenvia se não receber 200 OK em ~5s. Sem proteção, mensagens duplicadas viram tasks Celery duplicadas, métricas erradas, paciente recebendo o mesmo "vou verificar" duas vezes. Postgres rejeita reentrega no INSERT — antes de qualquer lógica.

## O que é

Postgres permite `UNIQUE` constraint com cláusula `WHERE` — só impõe a uniqueness em rows que satisfazem o predicado. Linhas fora do predicado coexistem livremente.

```sql
CREATE UNIQUE INDEX msg_canal_external_id_unico_se_presente
  ON public.mensagens
  USING btree (canal_id, external_id)
  WHERE (external_id IS NOT NULL);
```

Diferença pra `UNIQUE` total:

| Constraint | `(canal_A, NULL)` × `(canal_A, NULL)` | `(canal_A, "abc")` × `(canal_A, "abc")` |
|---|---|---|
| `UNIQUE (canal, external_id)` total | Aceita (NULLs são distintos em UNIQUE Postgres) ou rejeita (depende do `NULLS NOT DISTINCT`) | Rejeita |
| `UNIQUE ... WHERE external_id IS NOT NULL` (parcial) | **Aceita N rows com NULL** | Rejeita |

## Por que usamos no MedChat

Toda mensagem que entra no sistema vem de duas direções:

- **Recebida** do paciente (entrada): provedor entrega via webhook, sempre traz `external_id` (id do WhatsApp/Evolution).
- **Gerada** localmente pelo bot (saída): `external_id` começa NULL, vira o id do provedor só depois que `send_outbox` confirma envio.

Cenário 1 — recebida, com retry:
```
Evolution → POST /webhooks/.../canal_A  body={external_id="msg_abc", ...}
MedChat: INSERT INTO mensagens (canal_A, "msg_abc", ...) → OK, retorna 200
Evolution: timeout (não recebeu o 200) → retenta o mesmo POST 5s depois
MedChat: INSERT INTO mensagens (canal_A, "msg_abc", ...) → CONFLICT, retorna 200 mesmo assim (idempotente)
```

Sem o constraint, a segunda inserção criaria mensagem duplicada → bot dispara resposta 2x.

Cenário 2 — saída, várias mensagens em sequência:
```
bot decide responder com 2 frases:
  INSERT mensagens (canal_A, NULL, "primeira parte da resposta")  ← OK
  INSERT mensagens (canal_A, NULL, "segunda parte da resposta")   ← OK (não conflita com primeira)

send_outbox enviou ambas:
  UPDATE mensagens SET external_id="msg_xyz1" WHERE id=...  ← OK (xyz1 ainda não existia)
  UPDATE mensagens SET external_id="msg_xyz2" WHERE id=...  ← OK
```

Sem o `WHERE` parcial (com `UNIQUE` total), mensagens locais com `NULL` poderiam (dependendo da config Postgres) entrar em conflito entre si — bug.

Alternativas descartadas:

- **Dedup no app (`Mensagem.objects.filter(canal=..., external_id=...).exists()`)**: race condition entre 2 webhooks concorrentes. Dois INSERTs vão passar pelo check, ambos inserem.
- **Dedup com Redis lock**: dependência extra, exige disciplina (todo handler de webhook precisa pegar lock antes).
- **Dedup no Celery task (Idempotency-Key)**: tarde demais — a mensagem já tá no banco quando a task roda.

## Como aparece no código

`apps/conversations/models.py`:

```python
class Mensagem(TenantAwareModel):
    canal = models.ForeignKey(ClinicaCanal, on_delete=CASCADE, ...)
    external_id = models.CharField(max_length=256, null=True, blank=True, ...)
    # ... outros campos

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["canal", "external_id"],
                condition=models.Q(external_id__isnull=False),
                name="msg_canal_external_id_unico_se_presente",
            ),
        ]
```

Django gera o índice parcial Postgres correspondente.

No handler do webhook (Fase 2 — esboço):

```python
try:
    Mensagem.objects.create(
        canal=canal, external_id=payload["id"], ...
    )
except IntegrityError as e:
    if "msg_canal_external_id_unico_se_presente" in str(e):
        # Reentrega — ignorar e responder 200
        return 200
    raise
```

## Modelo / SDK / biblioteca usada

- Postgres `UNIQUE` parcial via index expression.
- Django ORM `models.UniqueConstraint(condition=...)` (Django 2.2+).

## Gotchas

- **Dedup no DB ≠ dedup no app inteiro.** Outras escritas que tocam estado (criar `EventoBot` de "mensagem recebida", incrementar contador) precisam tratar o `IntegrityError` e abortar gracefully — não podem rodar 2x mesmo que o INSERT da `Mensagem` falhe.
- **Erro do constraint precisa ser detectado por nome**, não por texto livre. O nome `msg_canal_external_id_unico_se_presente` é estável; mensagens de erro do Postgres mudam entre versões.
- **`canal_id` redundante na `Mensagem`**: já está na `Conversa` que ela aponta. Mantemos pra dedup sem JOIN — query do constraint só toca `mensagens`.
- **Atomicidade do INSERT**: o constraint roda dentro da transação. Se outro INSERT concorrente chega primeiro, o segundo encontra o conflito e falha. Sem race.
- **Saídas geradas localmente** (`external_id=NULL`) coexistem livres. Quando viram `external_id=<algo do provedor>` via `UPDATE`, aí sim o constraint passa a vigorar — e como o ID é único do provedor, não conflita.

## Notas relacionadas

- [[entidades/conversations]] — `Mensagem` é onde o constraint mora
- [[conceitos-ai/outbox-pattern]] — saídas começam `NULL`, ganham `external_id` depois do envio
- [[integracoes/evolution-api]] — provedor que reentrega
- [[conceitos-ai/exclude-using-gist]] — outro uso de constraint parcial (`WHERE status != 'cancelado'`)

## Referências externas

- [Postgres partial indexes](https://www.postgresql.org/docs/current/indexes-partial.html)
- [Django UniqueConstraint with condition](https://docs.djangoproject.com/en/5.0/ref/models/constraints/#uniqueconstraint)
- [Idempotency in distributed systems](https://en.wikipedia.org/wiki/Idempotence)
