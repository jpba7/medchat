---
tags: [meta, claude-code]
---

# Contrato com Claude Code

Convenções pro Claude Code operar em cima do vault. **Ler antes** de qualquer interação que envolva conhecimento estruturado do projeto.

## Grep-first (regra obrigatória)

Antes de responder sobre:

- Entidade nominada (`Clinica`, `Paciente`, `Agendamento`, `Conversa`, `Medico`, etc.).
- Tag de domínio ou setting (`clinica_id`, `app.clinica_id`, RLS, `BYPASSRLS`, `webhook_secret`, `outbox`).
- Integração externa (Evolution API, WhatsApp Cloud API, Anthropic SDK, OpenRouter, Langfuse, Celery).
- Fluxo de conversação (agendar, remarcar, cancelar, lembrete, handoff).
- Conceito AI (prompt caching, tool use, evals, RAG, agentic loop, RLS multi-tenant).

→ **`Grep -rn "termo" vault/ docs/`** primeiro. Se achar nota relevante:
1. Ler antes de responder.
2. Citar a nota usada na resposta (`vault/20-tech/anthropic-sdk.md`).

## Glob-before-link (regra obrigatória)

Antes de escrever `[[X]]` em qualquer resposta ou nota nova:

1. `Glob "vault/**/X*.md"` — confirmar que o alvo existe.
2. Se achar, escrever wiki-link.
3. Se **não achar**, **usar texto plano**, nunca criar wiki-link broken.

Wiki-link broken vira ghost node no graph view do Obsidian. Click → erro "Folder already exists" no Windows. Defesa em profundidade: este passo elimina a regressão.

## Path em backticks pra código

| Padrão | Resultado | Decisão |
|---|---|---|
| `[apps/x.py](../apps/x.py)` | Ghost node no graph | ❌ Nunca |
| `` `apps/clinics/models.py` `` | Texto literal, claro | ✅ Sempre |

Para arquivos `.md` em `docs/`, `CLAUDE.md`, `.claude/`: markdown link funciona porque vault-as-repo deixa todo `.md` visível.

```markdown
✅ [ADR 0002](../docs/adr/0002-rls-vs-schema.md)
✅ Ver `apps/clinics/models.py` → `Clinica.save()`
❌ Ver [Clinica.save()](../apps/clinics/models.py)
```

## Tags semânticas

Usar `tipo/<categoria>` pra tipo da nota — facilita filtro no Obsidian Tag Pane e Grep semântico:

- `tipo/entidade` — modelo do domínio.
- `tipo/fluxo` — fluxo de conversação.
- `tipo/conceito-ai` — padrão técnico genérico.
- `tipo/integracao` — provedor externo.
- `tipo/decisao` — escolha arquitetural pequena.
- `tipo/aprendizado` — gotcha, descoberta evolutiva.
- `tipo/diario` — daily note.

Plus tags por fase (`fase-1`, `fase-2`) ou tópico (`rls`, `webhook`, `caching`, `outbox`).

## Não criar se já existe

Antes de criar `vault/<categoria>/X.md`:

1. `Grep -rn "termo principal" vault/`.
2. Se achar nota relacionada:
   - Tópico igual → **atualizar a existente**, não criar nova.
   - Tópico relacionado mas distinto → **criar nova com link `[[]]`** pra existente.
3. Sem nada → criar nova.

Vault duplicado é vault morto.

## Idade da nota

Sem `created` ou `last_reviewed` no frontmatter. Pra saber idade:

```bash
git log -- vault/<path>
```

Mostra quando foi escrita/atualizada.

## Filtros (já configurados em `.obsidian/app.json`)

Excluído da indexação:

- `_templates/` — templates não viram nodes do graph.
- `apps/`, `medchat/`, `node_modules/`, `.venv/`, `build/`, `dist/` — código não-Markdown.
- `.claude/worktrees/` — worktrees operacionais.

## Captura via `/capture`

Quando detectar candidato vault-worthy durante conversa:

1. **Inline**: sinalizar com `💡 vault candidate: <descrição curta>`. **Não escrever no vault inline.**
2. **Batch no fim**: usuário roda `/capture`. Claude coleta, dedup via Grep, propõe diff por item, aprovação humana por item, escreve só o aprovado.

Filtros vault-worthy estão em `00-rules.md`. Filtros absolutos de não-captura (credenciais, PII, secrets) também lá.
