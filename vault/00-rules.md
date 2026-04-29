---
tags: [meta, vault-rules]
---

# Regras do Vault — MedChat

Vault de conhecimento atômico do MedChat. Operacional, lido pelo Claude Code via Grep-first, e renderizado limpo no Obsidian (vault-as-repo).

> **Em transição.** Esta é a base nova (PR 1 do redesign). Migração das 21 notas legadas de `vault/entidades/`, `vault/conceitos-ai/`, etc. pras pastas `10-domain/`, `20-tech/`, etc. acontece no PR seguinte. Por isso `00-index.md` ainda aponta pra estrutura antiga via `MOC.md`.

## Estrutura

```
vault/
├── 00-rules.md      ← este arquivo
├── 00-claude.md     ← contrato com Claude Code
├── 00-index.md      ← índice navegável (lazy MOC)
├── 10-domain/       ← entidades + fluxos do produto
├── 20-tech/         ← conceitos AI + integrações + padrões
├── 30-decisions/    ← decisões pequenas (ADRs grandes em docs/adr/)
├── 40-learnings/    ← gotchas, descobertas evolutivas
├── 90-journal/      ← daily notes
└── _templates/      ← templates (excluído da indexação Obsidian)
```

Numeração `10-`, `20-`, `30-`, `40-`, `90-` força ordenação consistente no sidebar do Obsidian. Flat dentro de cada pasta — zero subpastas.

## Frontmatter mínimo

```yaml
---
aliases:
  - WhatsApp Cloud API
tags: [tipo/integracao, fase-1]
---
```

Só `aliases` (opcional) e `tags`. **Nada de `title`, `type`, `created`, `last_reviewed`** — filename é canônico, idade vem de `git log`.

Tipo da nota vira tag: `tipo/entidade`, `tipo/fluxo`, `tipo/conceito-ai`, `tipo/integracao`, `tipo/decisao`, `tipo/aprendizado`, `tipo/diario`.

## Linking

| Alvo | Sintaxe | Exemplo |
|---|---|---|
| Nota interna ao vault | wiki-link | `[[clinica]]` ou `[[10-domain/clinica]]` |
| Markdown em `docs/` | markdown link relativo | `[ADR 0002](../docs/adr/0002-rls-vs-schema.md)` |
| Código (.py, .ts, etc.) | **backticks** | `` `apps/clinics/models.py` `` |

**Nunca** `[texto](path/arquivo.py)` — o Obsidian cataloga e cria ghost node no graph. Backticks resolvem (não-clicável, mas seguro).

## Naming

- `kebab-case` sempre (`agendar-consulta.md`).
- pt-BR pra termos de domínio (`clinica`, `paciente`, `agendamento`).
- Code identifiers preservados (`Agendamento`, `Clinica`, `clinica_id`).

## Captura via `/capture`

1. **Inline durante a conversa**: Claude detecta candidato vault-worthy e sinaliza com `💡 vault candidate: <descrição curta>`. **Não escreve no vault inline.**
2. **Batch no fim**: usuário roda `/capture`. Claude:
   - Coleta candidatos da sessão.
   - Pra cada um: `Grep` no vault pra detectar nota similar (dedup obrigatório).
   - Propõe nota nova OU update da existente (com diff explícito).
   - Espera aprovação humana por item antes de escrever.
   - Atualiza `00-index.md` se houver nota nova.

Detalhes: [`.claude/commands/capture.md`](../.claude/commands/capture.md).

## Vault-worthy

Sinalizar candidato apenas se atende **pelo menos um**:

- Conhecimento de domínio com motivo (regra com porquê, decisão arquitetural pequena).
- Detalhe operacional não-óbvio (gotcha, workaround, restrição escondida).
- Conexão entre entidades já no vault ("esse fluxo depende dessa integração").

**Não sinalizar**: status do dia, refactor trivial, coisas claras lendo código, reformulação sem novo insight.

## Não-captura (regras absolutas)

Nunca capturar no vault, mesmo se aparecer na conversa:

- Credenciais, senhas, chaves API, tokens, `webhook_secret` real.
- Strings de conexão completas com password.
- Dados pessoais de pacientes/médicos (CPF, telefone, endereço).
- Valores comerciais cliente-específicos.
- Conteúdo de `.env`, certificados, secrets.

Vault vai pra GitHub junto com código. **Privado ≠ seguro pra credencial.**

## Onde fica o quê — vault vs `docs/`

| Conteúdo | Lugar |
|---|---|
| Pedagogia longa estilo livro técnico (RLS deep dive, prompt caching deep dive) | [`docs/ai-engineering/`](../docs/ai-engineering/) |
| ADR formal grande com tradeoffs alternativos | [`docs/adr/`](../docs/adr/) |
| Plano de fase do projeto | [`docs/plans/`](../docs/plans/) |
| Contexto público macro (produto, stack, decisões MVP, histórico) | [`docs/context/`](../docs/context/) |
| Nota atômica por entidade/fluxo | `vault/10-domain/` |
| Nota atômica por conceito AI/integração | `vault/20-tech/` |
| Decisão pequena fora de ADR | `vault/30-decisions/` |
| Gotcha, descoberta evolutiva | `vault/40-learnings/` |
| Diário de sessão | `vault/90-journal/` |

`vault/20-tech/<x>.md` é nota curta com link pra `docs/ai-engineering/<x>.md` quando vira deep dive. Sem duplicação.

## Setup do Obsidian (1ª vez por máquina)

`.obsidian/` versionado no repo já trás a config canônica (templates folder, daily notes folder, ignore filters). Após `git clone`:

1. Abrir o **repo inteiro** no Obsidian (não só `vault/`). Vault-as-repo é o padrão.
2. Confirmar que `_templates/`, `apps/`, `medchat/`, `node_modules/`, `.venv/` estão excluídos da indexação (Settings → Files & Links → Excluded files → já populado via `app.json`).
3. Habilitar plugins core: file-explorer, search, switcher, graph, backlinks, daily-notes, templates (já em `core-plugins.json`).
