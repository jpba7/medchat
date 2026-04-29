---
title: clinica
type: entidade
tags: [tenant, raiz, clinica]
---

# `Clinica` (e `ClinicaCanal`, `ClinicaPolitica`)

> A clínica é o **cliente B2B** do MedChat. Cada linha de `Clinica` é um tenant. Tudo que tem `clinica_id` no produto inteiro aponta pra cá.

## Papel

`Clinica` define o tenant. Não é tenant-owned ela mesma — é a tabela que dá identidade pros tenants. Isso a torna a única tabela do produto que **não** tem `clinica_id` e **não** está sujeita a RLS.

`ClinicaCanal` e `ClinicaPolitica` são extensões diretas de configuração da clínica. Tenant-owned (têm `clinica_id`), mas conceitualmente "parte da raiz" — por isso vivem no mesmo app.

## Onde mora no código

- Modelo: [`apps/clinics/models.py`](../../apps/clinics/models.py)
  - `Clinica` (linha 30)
  - `ClinicaCanal` (linha 93)
  - `ClinicaPolitica` (linha 160)
- Base abstrata: [`apps/core/models.py`](../../apps/core/models.py) → `TenantAwareModel`
- Tabelas no banco: `clinicas`, `clinica_canais`, `clinica_politicas`

## Tenant-aware?

| Modelo | Tenant-owned? | RLS |
|---|---|---|
| `Clinica` | Não — É a tabela que define os tenants | Sem RLS |
| `ClinicaCanal` | Sim — herda `TenantAwareModel` | Com RLS |
| `ClinicaPolitica` | Sim — herda `TenantAwareModel` | Com RLS |

## Campos importantes — `Clinica`

| Campo | Tipo | Por quê existe |
|---|---|---|
| `id` | UUID | PK opaca, evita exposição de contagem por inteiro sequencial. |
| `slug` | SlugField unique | Header `X-Clinic-Slug` no painel resolve o tenant via slug. |
| `cnpj` | CharField(14) | Apenas dígitos, sem máscara. Permite mesma clínica vs sócios distintos. |
| `timezone` | IANA | Lembretes e horário comercial respeitam isso. Default `America/Sao_Paulo`. |
| `horario_comercial` | JSONB | Janelas de atendimento humano por dia da semana. Fora delas, bot responde mas **não** escala handoff. |
| `ativa` | bool | Soft-disable: webhooks ainda entram, mas tasks não disparam. Pra clientes em débito ou onboarding. |

## Campos importantes — `ClinicaCanal`

| Campo | Tipo | Por quê existe |
|---|---|---|
| `tipo` | TextChoices | `whatsapp_evolution` (MVP) ou `whatsapp_cloud` (produção). |
| `numero_e164` | CharField(16), indexed | Número WhatsApp da clínica em formato E.164. |
| `config` | JSONB | Credenciais/IDs do provedor sem schema rígido — Evolution e Cloud têm formatos diferentes. |
| `webhook_secret` | CharField(64) | Segredo HMAC do webhook. Auto-gerado via `secrets.token_urlsafe(32)`. **Rotacionar = deletar e salvar**. |
| `ativo` | bool, indexed | Desligar canal sem deletar. |

Constraint: `(clinica, tipo)` único — uma clínica não tem dois canais Evolution simultâneos.

## Campos importantes — `ClinicaPolitica`

Padrão chave-valor JSON. Permite adicionar regras sem migration. Exemplos de chaves usadas:

- `cancelamento_antecedencia_h` → int (horas mínimas pra cancelar)
- `cpf_obrigatorio` → bool (cobra CPF antes de agendar?)
- `lembrete_janelas_h` → list[int] (ex.: `[24, 2]` = 24h e 2h antes)
- `saudacao_bot` → str
- `horario_handoff_humano` → `{"inicio": "08:00", "fim": "18:00"}`

Constraint: `(clinica, chave)` único.

## Relacionamentos

- `Clinica` ← FK ← `ClinicaCanal` (via `clinica`, `on_delete=PROTECT`)
- `Clinica` ← FK ← `ClinicaPolitica` (via `clinica`, `on_delete=PROTECT`)
- `Clinica` ← FK ← qualquer outro modelo tenant-owned do produto (via herança de `TenantAwareModel`)

`on_delete=PROTECT` em todas as FKs pra `Clinica` é proposital: deletar uma clínica sem migration explícita não pode acontecer.

## Regras / invariantes

- **`Clinica` é a única tabela acessível antes do `RLSMiddleware` resolver o tenant.** O middleware lê daqui pra descobrir quem é o tenant da request, então não pode estar protegida por RLS.
- **`TenantAwareModel.save()` valida que `self.clinica_id` bate com `current_setting('app.clinica_id')`** (camada 2 da defesa). Se não bate, lança `ValidationError` com mensagem "vazamento cross-tenant".
- **Sem `app.clinica_id` setado, save abortar com `RuntimeError`** — não pode silenciar.
- **`webhook_secret` é gerado via callable**, não literal default — garante que cada `ClinicaCanal` novo recebe segredo distinto.

## Gotchas

- **`Clinica.ativa = False` não silencia webhooks**, só impede tasks. O webhook ainda valida HMAC e responde 200. Soft-disable, não hard-disable.
- **Rotacionar `webhook_secret`**: setar em branco e salvar. O `save()` do `ClinicaCanal` regenera quando vê string vazia. Não tem método `rotate_secret()` separado.
- **`cnpj` aceita string vazia** (`blank=True`). Não validar formato no model — validação fica na camada API/admin.
- **`config` JSONB sem schema**: cuidado ao ler. Sempre validar shape antes de usar (`config.get("instance_id")` em vez de `config["instance_id"]`).

## Notas relacionadas

- [[integracoes/evolution-api]] — usa `ClinicaCanal.config` e `webhook_secret`
- [[fluxos/agendar-consulta]] — toca `ClinicaPolitica` (`cancelamento_antecedencia_h`, `cpf_obrigatorio`)

## Referências externas

- [`docs/ai-engineering/07-multi-tenant-rls-postgres.md`](../../docs/ai-engineering/07-multi-tenant-rls-postgres.md) — pedagogia longa de RLS no MedChat.
- [`docs/adr/0002-rls-vs-schema.md`](../../docs/adr/0002-rls-vs-schema.md) — decisão formal RLS vs schema-per-tenant.
