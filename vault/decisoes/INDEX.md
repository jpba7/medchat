---
title: decisoes-index
type: decisao
tags: [index]
---

# Decisões — Índice

Decisões arquiteturais **grandes** vão pra [`docs/adr/`](../../docs/adr/) como ADR formal (regra do [`CLAUDE.md`](../../CLAUDE.md) §8). Esta pasta complementa: serve pra **decisões pequenas** que não justificam ADR mas vale registrar — escolhas de schema, gotchas resolvidas, padrões adotados ad-hoc.

## ADRs formais (em `docs/adr/`)

- [`0002-rls-vs-schema.md`](../../docs/adr/0002-rls-vs-schema.md) — RLS escolhido sobre schema-per-tenant pra multi-tenancy.

## Decisões pequenas (neste vault)

> Vazio até o primeiro caso aparecer.

Quando criar uma nota aqui:

1. Use [`vault/_templates/decisao.md`](../_templates/decisao.md).
2. Nomeie como `<slug-curto>.md` (ex.: `webhook-secret-rotacao.md`).
3. Adicione link aqui no INDEX.

## Quando vira ADR vs decisão pequena?

| Vai pra `docs/adr/` | Vai pra `vault/decisoes/` |
|---|---|
| Mexe em escolha de stack ou padrão amplo | Decisão local de uma feature |
| Tem alternativas com tradeoffs grandes | Tem 2-3 opções de implementação |
| Imutável depois de aceita | Pode ser revisitada |
| Afeta decisões futuras de arquitetura | Afeta um arquivo / um app |
