---
title: paciente
type: entidade
tags: [tenant-aware, entidade-central, lgpd]
---

# `Paciente`

> Entidade central do bot. Todo fluxo (agendar, cancelar, lembrar, escalar) começa resolvendo "quem é esse paciente?" a partir do número WhatsApp. Criado automaticamente pelo handler do webhook quando uma mensagem chega de um número desconhecido.

## Papel

Cada `Paciente` é uma pessoa que conversa via WhatsApp com uma clínica específica. **Mesmo número E.164 pode ser dois pacientes em duas clínicas diferentes** — paciente é tenant-owned. Um número conversa só pode existir 1× por clínica (unique `(clinica, telefone_e164)`).

## Onde mora no código

- Modelo: [`apps/patients/models.py`](../../apps/patients/models.py) → `Paciente`
- Migration: [`apps/patients/migrations/0001_initial.py`](../../apps/patients/migrations/) (commit `0b11361`)
- Tabela no banco: `pacientes`

## Tenant-aware?

- [x] **Sim** — herda de `TenantAwareModel`. Tem `clinica_id`. Sujeito a RLS.

## Campos importantes

| Campo | Tipo | Por quê existe |
|---|---|---|
| `telefone_e164` | CharField(16), indexed | Identificador primário no fluxo do bot. Formato com `+` + país (ex.: `+5511999999999`). |
| `nome` | CharField(200) | Resolvido do `pushName` do WhatsApp na primeira mensagem. Bot pode pedir confirmação depois. |
| `cpf` | CharField(14), nullable, indexed parcial | Apenas dígitos, sem máscara. Opcional por padrão; vira obrigatório se `ClinicaPolitica.cpf_obrigatorio=True`. |
| `lgpd_aceito_em` | DateTimeField, nullable | Timestamp do aceite do aviso LGPD. Enquanto NULL, bot apresenta `lgpd_texto` antes de qualquer outra interação. |
| `metadata` | JSONField | Dados auxiliares: `pushName` original, tags de segmentação, anotações livres. |

### Index parcial em `cpf`

```python
models.Index(
    fields=["cpf"],
    name="paciente_cpf_idx",
    condition=models.Q(cpf__isnull=False),
)
```

Index só inclui pacientes que preencheram CPF — reduz tamanho do índice quando a maioria não preenche (caso comum em clínicas que **não** exigem CPF).

## Relacionamentos

- `Clinica` ← FK ← `Paciente` (via `clinica`)
- `Paciente` ← FK ← `Conversa` (via `paciente`)
- `Paciente` ← FK ← `Agendamento` (via `paciente`)

## Regras / invariantes

- **Unique `(clinica, telefone_e164)`**: um número telefone aparece 1× por clínica. Se mesmo paciente pega celular novo, vira nova `Paciente` (a `Conversa` antiga continua referenciando a antiga). Se troca de número, é decisão de produto se mergeia ou não.
- **CPF é tenant-scoped**: dois `Paciente`s com mesmo CPF em clínicas diferentes são entidades distintas. Não há unique global por CPF (e nem deve haver — RLS impediria).
- **LGPD: bot deve apresentar texto da política `lgpd_texto` antes de qualquer outra interação enquanto `lgpd_aceito_em IS NULL`.** Sem aceite, não persistir mais dados que o mínimo (telefone + pushName).

## Gotchas

- **`pushName` do WhatsApp pode mentir.** É só a string que o cliente WhatsApp anuncia — paciente pode ter "Maria 🌸" como display name e ser João. Bot deve confirmar nome antes de marcar consulta importante.
- **CPF não é validado por algoritmo do dígito verificador no model** — só formato (apenas dígitos). Validação completa fica na camada API/admin se a clínica exigir.
- **`metadata` é JSONB sem schema.** Cuidado ao ler — sempre `metadata.get("chave", default)`.
- **Soft-delete não existe.** Deletar `Paciente` cascateia em conversas e agendamentos via `on_delete=CASCADE`. Decisão de produto: se cliente pede "esquecimento LGPD", o que apaga? (definir antes da Fase 2).

## Notas relacionadas

- [[entidades/clinica]] — `ClinicaPolitica.cpf_obrigatorio` controla se CPF é exigido
- [[entidades/catalog]] — `Medico` é a contraparte; agendamento liga os dois
- [[entidades/agendamento]] — usa `Paciente` como FK
- [[entidades/conversations]] — `Conversa` agrupa mensagens por `Paciente`
- [[fluxos/agendar-consulta]] — fluxo principal usa `Paciente`

## Referências externas

- [E.164 (números de telefone internacionais)](https://en.wikipedia.org/wiki/E.164)
- [LGPD — Lei nº 13.709/2018](https://www.gov.br/anpd/pt-br/assuntos/noticias/lei-geral-de-protecao-de-dados-pessoais-lgpd)
