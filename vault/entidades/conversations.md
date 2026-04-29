---
name: conversations
type: entidade
tags: [tenant-aware, conversa, mensagem, handoff, idempotencia]
---

# `Conversa`, `Mensagem`, `Handoff`

> Onde a conversa entre paciente e bot/atendente vira dado estruturado. 3 tabelas que juntas representam o histórico do canal e o estado da máquina (bot ativo / handoff aberto / encerrada).

## Papel

- **`Conversa`** — o "fio". Agrupa todas as mensagens trocadas com um paciente em um canal específico. Tem máquina de estados (`bot` ↔ `handoff_aguardando` ↔ `handoff_ativo` ↔ `encerrada`).
- **`Mensagem`** — cada turn (entrada do paciente ou saída do bot/atendente). **Unique parcial `(canal, external_id) WHERE external_id IS NOT NULL`** garante idempotência: webhook que reentrega não duplica.
- **`Handoff`** — registro de cada vez que a conversa precisou de humano. Múltiplos handoffs por conversa (atendente sai → bot retorna → outro handoff abre).

## Onde mora no código

- Modelo: [`apps/conversations/models.py`](../../apps/conversations/models.py)
- Migration: [`apps/conversations/migrations/0001_initial.py`](../../apps/conversations/migrations/) (commit `b69eeae`)
- Tabelas: `conversas`, `mensagens`, `handoffs`

## Tenant-aware?

| Modelo | Tenant-owned? | Notas |
|---|---|---|
| `Conversa` | Sim — `clinica_id` direto | Herda `TenantAwareModel`. |
| `Mensagem` | Sim — `clinica_id` **desnormalizado da `conversa`** | `save()` auto-popula. Defesa em profundidade. |
| `Handoff` | Sim — `clinica_id` **desnormalizado da `conversa`** | Idem. |

Razão da desnormalização: [[../decisoes/clinica-id-desnormalizado-vs-fk]].

## Campos — `Conversa`

| Campo | Tipo | Por quê existe |
|---|---|---|
| `paciente` | FK Paciente, CASCADE | Com quem a clínica está falando. |
| `canal` | FK ClinicaCanal, CASCADE | Por qual canal. (Mesmo paciente em canais diferentes = conversas diferentes.) |
| `status` | TextChoices, indexed | Ver máquina de estados abaixo. |
| `contexto` | JSONB | Estado **transitório** do fluxo bot — intenção detectada, slot fillers ("que dia?", "qual médico?"), flags. **Não é histórico de mensagens** (isso vai em `Mensagem`). |
| `encerrado_em` | DateTimeField, nullable | Timestamp de encerramento. NULL = ativa. |

### Máquina de estados

```
              ┌────────────────────┐
              │       bot          │  (estado normal)
              └─────┬─────────┬────┘
       handoff      │         │   bot encerra ou paciente some
       requisitado  │         ↓
                    ↓     ┌─────────────┐
        ┌─────────────┐   │  encerrada  │
        │ handoff_    │   └─────────────┘
        │ aguardando  │   (terminal — sem volta)
        └─────┬───────┘
   atendente  │
   aceita     ↓
        ┌─────────────┐
        │ handoff_    │ ──── bot retoma ────┐
        │ ativo       │                     │
        └─────────────┘                     │
                                            ↓
                                     volta para `bot`
                                     (cria novo Handoff
                                      depois se precisar)
```

Indexes:
- `(clinica, status)` — inbox humano: "quem precisa de atendente agora".
- `(paciente, -criado_em)` — histórico do paciente, mais recente primeiro.

## Campos — `Mensagem`

| Campo | Tipo | Por quê existe |
|---|---|---|
| `conversa` | FK Conversa, CASCADE | A qual fio pertence. |
| `canal` | FK ClinicaCanal, CASCADE | **Redundante** (mesmo da conversa) — preenchido pra queries de idempotência sem JOIN. |
| `direcao` | TextChoices(`entrada`, `saida`) | Recebida (paciente → sistema) ou enviada (sistema → paciente). |
| `remetente` | CharField(256) | E.164 do paciente em entradas; nome do bot ou ID do atendente em saídas. |
| `conteudo` | TextField | Texto da mensagem. |
| `payload_raw` | JSONB | Payload bruto do provedor (Evolution/Cloud) pra debug. |
| `external_id` | CharField(256), nullable, indexed | ID atribuído pelo provedor. **NULL em mensagens geradas localmente que ainda não foram enviadas.** |

### Constraint principal — idempotência via unique parcial

```python
models.UniqueConstraint(
    fields=["canal", "external_id"],
    condition=models.Q(external_id__isnull=False),
    name="msg_canal_external_id_unico_se_presente",
)
```

Webhook reentrega bate o conflict; saídas locais com `NULL` coexistem. Ver [[../conceitos-ai/idempotencia-via-unique-parcial]].

`clean()` valida `canal == conversa.canal`.

## Campos — `Handoff`

| Campo | Tipo | Por quê existe |
|---|---|---|
| `conversa` | FK Conversa, CASCADE | A qual fio pertence. |
| `gatilho` | TextChoices | `pedido_explicito`, `confianca_baixa`, `urgencia_medica`, `reclamacao`. Por que o bot escalou. |
| `aceito_por` | CharField, nullable | Identificador do atendente que assumiu (livre por enquanto). |
| `encerrado_em` | DateTimeField, nullable | NULL = handoff em aberto. |
| `resolucao` | TextField, nullable | Resumo livre de como o atendimento foi resolvido. |

Múltiplos `Handoff`s por `Conversa` são esperados — ver máquina de estados acima.

Indexes:
- `(clinica, -criado_em)` — inbox humano por clínica.
- `(conversa)` — buscar handoffs de uma conversa específica.

## Relacionamentos

- `Clinica` ← FK ← `Conversa`, `Mensagem`, `Handoff`
- `Paciente` ← FK (CASCADE) ← `Conversa`
- `ClinicaCanal` ← FK (CASCADE) ← `Conversa`, `Mensagem`
- `Conversa` ← FK (CASCADE) ← `Mensagem`, `Handoff`

## Regras / invariantes

- **Idempotência de webhook**: reentrega bate `IntegrityError` no constraint parcial → handler responde 200 sem reprocessar.
- **`Mensagem.canal` deve bater com `conversa.canal`**: validado em `clean()`.
- **`Mensagem.clinica_id` desnormalizado** auto-populado via `save()` antes da validação `TenantAwareModel.save()` rodar.
- **`Handoff.encerrado_em IS NULL`** marca o handoff "atual" da conversa. Conversa pode ter N handoffs no histórico, no máximo 1 sem `encerrado_em`.

## Gotchas

- **`canal` em `Mensagem` é redundante** mas necessário pro constraint parcial — sem ele, pra impor unique `(canal, external_id)` precisaria JOIN com conversa em cada INSERT.
- **`external_id` em saídas só é preenchido depois** que `send_outbox` confirma envio com o provedor. Antes disso, NULL. **Importante pra evitar bug**: se você query `Mensagem.objects.filter(external_id=algum)` e esquece o NULL, ignora saídas pendentes.
- **`payload_raw` JSONB livre**: cuidado ao ler. Schemas variam entre Evolution e Cloud API.
- **`Handoff.gatilho` é input do bot/sistema**, não do paciente. Não confundir com motivo escrito pelo paciente (que vai em `mensagens` mesmo).
- **Soft-delete não existe em nenhuma das 3.** Deletar `Conversa` cascateia em mensagens e handoffs (via CASCADE).

## Notas relacionadas

- [[clinica]] — `ClinicaCanal` é o canal
- [[paciente]] — `Paciente` é o outro lado da conversa
- [[outbox]] — `send_outbox` atualiza `Mensagem.external_id` após envio
- [[../conceitos-ai/idempotencia-via-unique-parcial]] — explicação detalhada da unique parcial
- [[../decisoes/clinica-id-desnormalizado-vs-fk]] — desnormalização defesa em profundidade
- [[../integracoes/evolution-api]] — provedor que entrega webhooks
- [[../fluxos/agendar-consulta]] — fluxo passa por `Conversa` + `Mensagem`s
