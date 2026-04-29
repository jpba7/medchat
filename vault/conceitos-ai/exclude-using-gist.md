---
name: exclude-using-gist
type: conceito-ai
tags: [postgres, constraint, agendamento, anti-overlap]
---

# `EXCLUDE USING GIST` — anti-overlap atômico no banco

> Ao invés de o bot "ler agenda + decidir + inserir" (com janela de race entre essas 3 etapas), o Postgres garante atomicamente que dois agendamentos ATIVOS do mesmo médico não se sobrepõem no tempo. Garantia no INSERT, não na aplicação.

## O que é

`EXCLUDE` é uma `Constraint` Postgres que generaliza `UNIQUE`. `UNIQUE` rejeita rows com valores **iguais**; `EXCLUDE` rejeita com valores que satisfazem **qualquer operador binário** — o operador é parametrizável.

`USING GIST` diz que o índice de suporte é GIST (tipo de índice que sabe avaliar operadores de range, geometria, etc.). GIST nativo só conhece operadores não-equality; pra incluir `=` precisa da extension **`btree_gist`**.

`tstzrange(start, end)` constrói um range temporal a partir de duas colunas escalares. O operador `&&` é "overlaps" — retorna true se dois ranges se cruzam.

## Por que usamos no MedChat

Agendamento de consulta médica tem invariante crítica: **dois agendamentos ATIVOS do mesmo médico não podem ocupar tempos sobrepostos**. Quem garante isso?

- **Aplicação ("ler agenda → decidir → inserir")** tem race condition. Dois pacientes pedem o mesmo slot ao mesmo tempo, ambos veem agenda livre, ambos inserem. Resultado: overlap.
- **Lock distribuído em Redis** funciona, mas exige disciplina — todo INSERT precisa pegar o lock antes; se algum caminho esquece, vaza. E adiciona dependência (Redis vivo) pra um INSERT de banco.
- **Constraint no Postgres** resolve sem race: o INSERT ou passa (não há overlap) ou falha imediatamente (Postgres rejeita). Atomicidade do banco já cuida.

Alternativas descartadas:

- **Lock distribuído Redis**: dependência extra, exige disciplina humana, falha aberta se alguém esquece.
- **Aplicação com `SELECT ... FOR UPDATE`**: serializa por médico/dia. Funciona mas é mais frágil que o constraint nativo (e exige transação cuidadosa).

## Como aparece no código

Definição no Django ORM (`apps/appointments/models.py`):

```python
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db.models import F, Func, Q

class TstzRange(Func):
    """Wrapper Django para tstzrange(start, end) SQL."""
    function = "tstzrange"
    output_field = DateTimeRangeField()

class Agendamento(TenantAwareModel):
    # ...campos...
    inicio_em = models.DateTimeField()
    fim_em = models.DateTimeField()
    status = models.CharField(...)  # 'agendado', 'realizado', 'cancelado', 'nao_compareceu'

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="agendamento_sem_overlap_por_medico",
                expressions=[
                    ("medico", RangeOperators.EQUAL),
                    (TstzRange("inicio_em", "fim_em"), RangeOperators.OVERLAPS),
                ],
                condition=~Q(status="cancelado"),
            ),
        ]
```

SQL gerado (aproximado):

```sql
ALTER TABLE agendamentos
ADD CONSTRAINT agendamento_sem_overlap_por_medico
EXCLUDE USING GIST (
    medico_id WITH =,
    tstzrange(inicio_em, fim_em) WITH &&
) WHERE (status != 'cancelado');
```

Pre-requisito: extension habilitada no banco:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

(Migration `apps/core/migrations/0001_rls_setup.py` já habilita junto com o setup geral.)

### O `WHERE` parcial é importante

`WHERE (status != 'cancelado')` exclui canceladas do check. Significado: vaga liberada por cancelamento pode ser reocupada. Status `realizado` e `nao_compareceu` continuam ATIVOS na constraint — não dá pra rebookar uma consulta que já aconteceu (preserva histórico imutável).

## Modelo / SDK / biblioteca usada

- Postgres ≥9.0 (constraint), extension `btree_gist`.
- Django ORM `django.contrib.postgres.constraints.ExclusionConstraint` (Django 4.1+).
- `django.contrib.postgres.fields.DateTimeRangeField` pra tipar o output do `TstzRange`.

## Gotchas

- **`btree_gist` é extension separada.** Postgres normal não vem com ela; precisa `CREATE EXTENSION btree_gist`. Se a constraint compilar mas o INSERT falhar com "data type uuid has no default operator class for access method 'gist'", é falta de extension.
- **`tstzrange` é exclusivo no fim por padrão (`[start, end)`)**. Dois agendamentos `[10:00, 11:00)` e `[11:00, 12:00)` **NÃO** se sobrepõem (11:00 está no segundo, não no primeiro). É o comportamento que queremos.
- **`condition` (`WHERE`) precisa ser literal seguro pelo Postgres**. No nosso caso usamos `~Q(status="cancelado")` — string literal "cancelado", não a inner class `Status.CANCELADO`. Por quê? Porque dentro de `Meta`, a inner class `Status` ainda não está acessível pelo nome curto (escopo de classe sendo construído).
- **Validação acontece no INSERT/UPDATE**, não em `clean()` Python. Se você criar agendamento "à força" via SQL bruto, ainda assim o Postgres rejeita.

## Notas relacionadas

- [[entidades/agendamento]] — onde a constraint é definida
- [[fluxos/agendar-consulta]] — fluxo que se beneficia (sem race condition)
- [[conceitos-ai/idempotencia-via-unique-parcial]] — outro caso de constraint parcial Postgres pra invariante de domínio

## Deep dive

- (a criar) `docs/ai-engineering/<NN>-postgres-exclusion-constraint.md` — pedagogia longa, se valer.

## Referências externas

- [Postgres EXCLUDE constraint](https://www.postgresql.org/docs/current/sql-altertable.html#SQL-ALTERTABLE-EXCLUDE-CONSTRAINT)
- [`btree_gist` extension](https://www.postgresql.org/docs/current/btree-gist.html)
- [Django `ExclusionConstraint`](https://docs.djangoproject.com/en/5.0/ref/contrib/postgres/constraints/#exclusionconstraint)
- [Range types Postgres](https://www.postgresql.org/docs/current/rangetypes.html)
