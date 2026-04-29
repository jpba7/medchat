---
name: agendamento
type: entidade
tags: [tenant-aware, agendamento, exclusion-constraint, anti-overlap]
---

# `Agendamento`

> Onde o produto materializa valor: paciente escolheu médico+convênio+horário e o bot ou atendente registrou a consulta. A invariante mais forte do schema vive aqui — **dois agendamentos ATIVOS do mesmo médico não podem se sobrepor no tempo**. Postgres impõe isso atomicamente, não a aplicação.

## Papel

`Agendamento` representa uma consulta marcada. Ciclo de vida via `status`:

- `agendado` — marcado, ativo (ocupa o slot)
- `realizado` — aconteceu (ocupa o slot historicamente — não dá pra rebookar)
- `nao_compareceu` — paciente faltou (idem; ocupa)
- `cancelado` — cancelado (slot LIBERADO — pode reocupar)

## Onde mora no código

- Modelo: [`apps/appointments/models.py`](../../apps/appointments/models.py) → `Agendamento`
- Wrapper SQL: classe interna `TstzRange` (Func) — wrapper do Postgres `tstzrange(start, end)`
- Migration: [`apps/appointments/migrations/0001_initial.py`](../../apps/appointments/migrations/) (commit `a9bcb07`)
- Tabela: `agendamentos`

## Tenant-aware?

- [x] **Sim** — herda de `TenantAwareModel`. RLS.

## Campos importantes

| Campo | Tipo | Por quê existe |
|---|---|---|
| `paciente` | FK Paciente, CASCADE | Quem agendou. |
| `medico` | FK Medico, CASCADE | Com quem. |
| `convenio` | FK Convenio, **PROTECT** | Plano usado. PROTECT impede deletar convênio que tem agendamento. |
| `inicio_em` | DateTimeField, indexed | Início (timestamptz). |
| `fim_em` | DateTimeField | Calculado pelo bot a partir de `inicio_em + medico.duracao_consulta_min`. **Explícito no schema porque a constraint precisa do range.** |
| `status` | TextChoices, indexed | Ver ciclo de vida acima. |
| `origem` | TextChoices | `bot`, `humano`, `import`. Por onde entrou no sistema. |
| `external_event_id` | CharField, nullable, indexed | Prep pra sync com calendário externo (Google/Outlook) na Fase 2+. NULL hoje. |
| `external_provider` | TextChoices | `google_calendar`, `outlook`, `apple`. Apenas com `external_event_id`. |
| `cancelado_motivo` | TextField, nullable | Texto livre do motivo. |

## Constraints — coração da entidade

### 1. `agendamento_inicio_antes_de_fim` (CheckConstraint)

```python
models.CheckConstraint(
    condition=Q(inicio_em__lt=F("fim_em")),
    name="agendamento_inicio_antes_de_fim",
)
```

Tempo invariante: `fim > inicio`. Evita registros corrompidos antes da exclusion constraint avaliar overlap.

### 2. `agendamento_sem_overlap_por_medico` (ExclusionConstraint)

```python
ExclusionConstraint(
    name="agendamento_sem_overlap_por_medico",
    expressions=[
        ("medico", RangeOperators.EQUAL),
        (TstzRange("inicio_em", "fim_em"), RangeOperators.OVERLAPS),
    ],
    condition=~Q(status="cancelado"),
)
```

SQL gerado:

```sql
EXCLUDE USING GIST (
    medico_id WITH =,
    tstzrange(inicio_em, fim_em) WITH &&
) WHERE (status != 'cancelado');
```

**Garante atomicamente que dois `Agendamento` com mesmo `medico_id` e tempos sobrepostos não podem coexistir, exceto se um deles está cancelado.** Ver [[conceitos-ai/exclude-using-gist]] pra explicação completa.

Pre-requisito: extension `btree_gist` (habilitada na migration `core/0001_rls_setup`).

## Indexes

- `(clinica, inicio_em, status)` — query principal "agenda da clínica X em ordem cronológica filtrada por status".
- `(paciente, status)` — query "agendamentos abertos do paciente Y".

## Relacionamentos

- `Clinica` ← FK ← `Agendamento`
- `Paciente` ← FK (CASCADE) ← `Agendamento`
- `Medico` ← FK (CASCADE) ← `Agendamento`
- `Convenio` ← FK (PROTECT) ← `Agendamento`

## Regras / invariantes

- **Cross-tenant blockado em `clean()`**: `paciente`, `medico`, `convenio` precisam ter mesmo `clinica_id` que o agendamento.
- **`fim_em` derivado**: a aplicação calcula a partir de `medico.duracao_consulta_min`. Migration não tem default — campo é obrigatório.
- **Vaga liberada via cancelamento**: cancelado entra no `WHERE NOT IN` da exclusion constraint, então slot pode ser reocupado por outro agendamento.
- **Histórico imutável**: `realizado` e `nao_compareceu` ocupam o slot pra sempre. Não dá pra "remarcar uma consulta passada" — cria nova.

## Gotchas

- **`tstzrange` é exclusivo no fim por padrão (`[start, end)`)**. `[10:00, 11:00)` e `[11:00, 12:00)` **NÃO** se sobrepõem. Bom: encaixe perfeito. Atenção: se a aplicação usar `[start, end]` em outro lugar, alinhar.
- **Exclusion constraint usa string literal `"cancelado"`**, não `Status.CANCELADO`. Por quê? Inner class ainda não tá acessível dentro de `Meta` (escopo de classe sendo construído). Migration mostra a string crua.
- **`origem` rastreia origem da escrita, não atualizações**. Cancelamento pelo paciente via bot mantém `origem='bot'` mesmo se o registro foi modificado.
- **`external_event_id` indexed** mesmo sendo nullable. Index parcial implícito (Postgres não indexa NULL por default). Quando Fase 2+ liga calendário, queries por `external_event_id` ficam rápidas.
- **`PROTECT` em convênio**: deletar convênio que tem agendamento não dá. Pra remover convênio antigo, primeiro arquivar agendamentos relacionados (definir convenção depois).

## Notas relacionadas

- [[entidades/paciente]], [[entidades/catalog]] — FKs
- [[conceitos-ai/exclude-using-gist]] — explicação detalhada da exclusion constraint
- [[fluxos/agendar-consulta]] — fluxo principal cria `Agendamento` ao final
- [[aprendizados/medchat-superuser-bypassrls]] — `clean()` cross-tenant é defesa em profundidade contra BYPASSRLS

## Referências externas

- [`btree_gist`](https://www.postgresql.org/docs/current/btree-gist.html)
- [Postgres range types](https://www.postgresql.org/docs/current/rangetypes.html)
- [Django ExclusionConstraint](https://docs.djangoproject.com/en/5.0/ref/contrib/postgres/constraints/#exclusionconstraint)
