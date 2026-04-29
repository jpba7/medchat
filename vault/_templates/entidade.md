---
name: <slug-da-entidade>
type: entidade
tags: []
---

# `<NomeDoModelo>`

> Frase única de contexto: o que essa entidade É no domínio do MedChat.

## Papel

O que esta entidade representa no produto. 1-3 linhas.

## Onde mora no código

- Modelo: `apps/<app>/models.py` → classe `<NomeDoModelo>`
- Migration relevante: `apps/<app>/migrations/<NNNN>_<nome>.py`
- Tabela no banco: `<db_table>`

## Tenant-aware?

- [ ] Sim — herda de `TenantAwareModel`. Tem `clinica_id`. Sujeito a RLS.
- [ ] Não — global. Não tem `clinica_id`.

## Campos importantes

| Campo | Tipo | Por quê existe |
|---|---|---|
| `<campo>` | `<tipo>` | {motivo curto, 1 linha} |

## Relacionamentos

- `<NomeDoModelo>` ← FK ← `<OutroModelo>` (via `<campo>`)
- `<NomeDoModelo>` → FK → `<OutroModelo>` (via `<campo>`)

## Regras / invariantes

- {regra de negócio com motivo}
- {invariante que precisa ser preservado}

## Gotchas

- {armadilha não-óbvia que vale documentar}

## Notas relacionadas

- `[[fluxos/<fluxo-que-toca-essa-entidade>]]`
- `[[integracoes/<integracao-relacionada>]]`
- `[[conceitos-ai/<conceito-relacionado>]]`

## Referências externas

- [`docs/<doc-pedagogico>.md`](../../docs/) — deep dive relacionado, se houver.
