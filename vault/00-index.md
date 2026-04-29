---
tags: [meta, indice]
---

# Índice — Vault MedChat

> **Em transição.** Estrutura nova (`10-domain/`, `20-tech/`, etc.) está vazia neste PR. Migração das 21 notas legadas acontece no próximo PR. Os links abaixo apontam pra `MOC.md` legado enquanto isso.

## Estrutura nova (em construção)

- `10-domain/` — entidades + fluxos do produto MedChat.
- `20-tech/` — conceitos AI + integrações + padrões técnicos.
- `30-decisions/` — decisões pequenas (ADRs grandes em `docs/adr/`).
- `40-learnings/` — gotchas, descobertas evolutivas.
- `90-journal/` — daily notes.
- `_templates/` — templates (excluído da indexação).

## Notas atuais (estrutura legada — migração no próximo PR)

- [[MOC]] — índice navegável da estrutura antiga.

## Documentação fora do vault

- [`docs/adr/`](../docs/adr/) — ADRs formais.
- [`docs/ai-engineering/`](../docs/ai-engineering/) — pedagogia longa de conceitos AI.
- [`docs/plans/`](../docs/plans/) — roadmap de fases.
- [`docs/context/`](../docs/context/) — contexto macro do produto.

Vault-as-repo deixa esses paths navegáveis direto no Obsidian.

## Como navegar

- **Por entidade do produto**: começa em `10-domain/<nome>` quando migração rolar.
- **Por conceito técnico**: `20-tech/<nome>`.
- **Por dúvida pontual**: `Grep -rn "termo" vault/ docs/`.
