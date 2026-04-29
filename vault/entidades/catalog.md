---
name: catalog
type: entidade
tags: [tenant-aware, catalog, vocabulario, agendamento]
---

# `Especialidade`, `Medico`, `Convenio`, `MedicoConvenio`, `MedicoDisponibilidade`

> Vocabulário de agendamento da clínica — o "menu" que o paciente vê. Bot usa pra classificar pedido ("preciso de cardiologista") e listar opções concretas (médicos disponíveis, convênios aceitos, horários).

## Papel

5 modelos no app `catalog` formam o que cada clínica oferece:

- **`Especialidade`**: área de atuação. Ex.: Cardiologia, Pediatria.
- **`Medico`**: profissional. CRM + especialidade + duração default da consulta.
- **`Convenio`**: plano de saúde aceito. Ex.: Unimed, Bradesco Saúde.
- **`MedicoConvenio`** (through table): vínculo médico × convênio + preço.
- **`MedicoDisponibilidade`**: faixa horária semanal recorrente de atendimento.

Todos tenant-owned (RLS) — clínicas não compartilham nada do catálogo.

## Onde mora no código

- Modelo: [`apps/catalog/models.py`](../../apps/catalog/models.py)
- Migrations:
  - [`0001_initial.py`](../../apps/catalog/migrations/) — `Especialidade`, `Medico`, `Convenio` (commit `52bf9b8`)
  - [`0002_*`](../../apps/catalog/migrations/) — `MedicoConvenio`, `MedicoDisponibilidade` (commit `118c015`)
- Tabelas: `especialidades`, `medicos`, `convenios`, `medico_convenios`, `medico_disponibilidades`

## Tenant-aware?

| Modelo | Tenant-owned? |
|---|---|
| `Especialidade` | Sim — `clinica_id` direto |
| `Medico` | Sim — `clinica_id` direto |
| `Convenio` | Sim — `clinica_id` direto |
| `MedicoConvenio` | Sim — `clinica_id` **desnormalizado do FK** `medico` |
| `MedicoDisponibilidade` | Sim — `clinica_id` **desnormalizado do FK** `medico` |

Decisão de desnormalizar `clinica_id` em `MedicoConvenio` e `MedicoDisponibilidade` (em vez de derivar via JOIN) é **defesa em profundidade** — ver [[../decisoes/clinica-id-desnormalizado-vs-fk]].

## Campos importantes — `Especialidade`

| Campo | Tipo | Por quê existe |
|---|---|---|
| `nome` | CharField(100) | Texto livre. Unique `(clinica, nome)`. |
| `ativo` | bool, indexed | Soft-disable. Bot ignora especialidades inativas. |

## Campos importantes — `Medico`

| Campo | Tipo | Por quê existe |
|---|---|---|
| `nome` | CharField(200) | Display do médico. |
| `crm` | CharField(20) | Formato `NÚMERO/UF`, ex.: `123456/SP`. Unique `(clinica, crm)` evita duplicata acidental. |
| `especialidade` | FK Especialidade, **PROTECT**, **nullable** | Nullable durante onboarding (médico cadastrado antes de ter especialidade). Bot só lista médicos com especialidade. PROTECT bloqueia deletar especialidade que ainda tem médico. |
| `duracao_consulta_min` | PositiveSmallInt(default=30) | Duração padrão. Usado pra gerar slots livres. |
| `ativo` | bool, indexed | Soft-disable. |

`clean()` valida que `especialidade.clinica_id == self.clinica_id` — sem isso, admin com BYPASSRLS poderia plugar especialidade da clínica B em médico da clínica A. RLS impede leitura mas não escrita. Defesa em profundidade.

## Campos importantes — `Convenio`

| Campo | Tipo | Por quê existe |
|---|---|---|
| `nome` | CharField(100) | Display. Unique `(clinica, nome)`. |
| `ativo` | bool | Soft-disable. |

Cadastro independente de médico — clínica pode aceitar Unimed mesmo que nenhum médico atenda Unimed ainda. Relação concreta vive em `MedicoConvenio`.

## Campos importantes — `MedicoConvenio`

| Campo | Tipo | Por quê existe |
|---|---|---|
| `medico` | FK Medico, CASCADE | Vínculo. |
| `convenio` | FK Convenio, CASCADE | Vínculo. |
| `preco_consulta_centavos` | PositiveInt, nullable | Preço específico desse vínculo (em centavos). NULL = usa preço default da clínica/convênio definido em política. |
| `ativo` | bool | Médico aceita esse convênio agora ou não. |

Constraint: `unique (medico, convenio)`.

`save()` auto-popula `clinica_id` do FK `medico` antes do `super().save()` validar contra `app.clinica_id`. `clean()` valida que `medico.clinica_id == convenio.clinica_id` — proibido um médico de A vinculado a convênio de B.

## Campos importantes — `MedicoDisponibilidade`

| Campo | Tipo | Por quê existe |
|---|---|---|
| `medico` | FK Medico, CASCADE | A quem se aplica. |
| `dia_semana` | IntegerChoices (0-6) | Segunda=0, Domingo=6. |
| `inicio` | TimeField | Hora local da clínica (timezone do tenant). |
| `fim` | TimeField | `clean()` valida `inicio < fim`. |

Permite **múltiplas faixas/dia** (manhã + tarde com almoço entre) — não há unique `(medico, dia_semana)`. Cálculo de slots livres = união das faixas - agendamentos marcados.

## Relacionamentos

- `Clinica` ← FK ← `Especialidade`, `Medico`, `Convenio`, `MedicoConvenio`, `MedicoDisponibilidade`
- `Especialidade` ← FK (PROTECT, nullable) ← `Medico`
- `Medico` ← FK (CASCADE) ← `MedicoConvenio`
- `Convenio` ← FK (CASCADE) ← `MedicoConvenio`
- `Medico` ← FK (CASCADE) ← `MedicoDisponibilidade`
- `Medico`, `Convenio` ← FK ← `Agendamento`

## Regras / invariantes

- **CRM unique por clínica** — duplicata acidental no cadastro é bloqueada.
- **Especialidade nullable em `Medico`** — onboarding pode começar sem ela. Bot filtra `.filter(especialidade__isnull=False)`.
- **`MedicoConvenio` e `MedicoDisponibilidade` desnormalizam `clinica_id`** automaticamente via `save()`. Defesa em profundidade.
- **`MedicoDisponibilidade` em hora local da clínica** (não UTC) — `Clinica.timezone` define a janela real.

## Gotchas

- **CRM não é validado por dígito verificador** — só formato livre. Validação real fica em painel/API se a clínica precisar.
- **PROTECT em `Medico.especialidade`** — não dá pra deletar especialidade enquanto tem médico apontando. Pra remover especialidade, primeiro re-atribuir os médicos.
- **`MedicoDisponibilidade.dia_semana`**: convenção 0=Segunda, 6=Domingo. Diferente de Python `datetime.weekday()` (que também é 0-6 com Segunda=0) — coerente, mas atenção pra não confundir com `isoweekday()` (1-7).
- **Múltiplas faixas no mesmo dia podem se sobrepor.** Não há constraint impedindo (caso de uso: "manhã 08-12" + "tarde 14-18"). Cálculo de slots tem que tratar overlap.

## Notas relacionadas

- [[clinica]] — `Clinica` é raiz; `ClinicaPolitica` define preço default por convênio
- [[paciente]] — `Paciente` agenda com `Medico` que tem `MedicoConvenio` aceito
- [[agendamento]] — referencia `Medico` e `Convenio`
- [[../decisoes/clinica-id-desnormalizado-vs-fk]] — explica desnormalização das through-tables
- [[../fluxos/agendar-consulta]] — fluxo usa esses modelos pra montar resposta
