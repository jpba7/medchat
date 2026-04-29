# Vault — Regras de Operação

Base de conhecimento atômica do MedChat. Captura conhecimento que **não vive bem no código** nem em `docs/` longo: regra de domínio com motivo, gotcha de integração, conexão entre entidades, decisão pequena fora de ADR, fluxo de conversação, conceito AI usado no produto.

Usado por Claude Code em sessões deste repo, e por humanos lendo direto.

## Estrutura

```
vault/
├── entidades/        ← uma nota por entidade do domínio (atômico)
├── conceitos-ai/     ← uma nota por conceito AI usado (links pra docs/ai-engineering/)
├── integracoes/      ← uma nota por integração externa
├── fluxos/           ← uma nota por fluxo de conversação WhatsApp
├── decisoes/         ← INDEX.md → docs/adr/ + decisões menores
├── aprendizados/     ← descobertas evolutivas (narrativo)
├── diario/           ← YYYY-MM-DD.md, fluxo livre
│   └── _arquivo/     ← entradas > 30 dias
├── _templates/       ← templates de nota
├── README.md         ← este arquivo
└── MOC.md            ← Map of Content (índice navegável)
```

## Frontmatter padrão

Toda nota tem frontmatter YAML mínimo:

```yaml
---
name: <identificador curto, único>
type: entidade | conceito-ai | integracao | fluxo | decisao | aprendizado | diario
tags: [...]   # opcional, ajuda navegação Obsidian
---
```

Sem `created`, `last_reviewed`, `ttl_days`, `source`. Pra saber idade de uma nota: `git log -- vault/<path>`.

## Idioma

Mesma regra do [`CLAUDE.md`](../CLAUDE.md):

- **Narrativa, explicação, contexto de domínio**: pt-BR.
- **Identifiers de código** (paths, classes, funções, env vars, nomes de modelos Django): preservar como existem no código, **sem traduzir**.
- **Termos de domínio em pt-BR** (clínica, médico, paciente, agendamento, remarcar, cancelar, lembrete, handoff): nunca traduzir pra inglês.

Bom: *"O modelo `Clinica` é a raiz da tenancy. Não é tenant-owned — é a tabela que DEFINE os tenants."*
Ruim: *"The `Clinica` model is the tenancy root. It is not tenant-owned — it's the table that DEFINES tenants."*

## Captura (`/capture` slash command)

Slash command em [`.claude/commands/capture.md`](../.claude/commands/capture.md). Fluxo:

1. **Inline durante a conversa**: Claude detecta candidatos vault-worthy e sinaliza com `💡 vault candidate: <descrição curta>`. **Não escreve no vault inline** — só sinaliza.
2. **Batch no fim da sessão**: usuário roda `/capture`. Claude:
   1. Coleta todos os candidatos sinalizados na sessão.
   2. Pra cada um: `Grep` no vault pra detectar nota similar.
   3. Apresenta proposta — nota nova OU update da existente (com diff explícito).
   4. Espera aprovação humana antes de escrever.
   5. Atualiza [`MOC.md`](MOC.md) se houver nota nova.

### Filtro vault-worthy

Sinalize candidato apenas se atende **pelo menos um**:

- **Conhecimento de domínio com motivo** — regra de negócio, comportamento que precisa de explicação, decisão arquitetural pequena com porquê.
- **Detalhe operacional não-óbvio** — gotcha, workaround, restrição escondida, comportamento que sumiria em `git log` a longo prazo.
- **Conexão entre entidades já existentes no vault** — "esse fluxo depende dessa integração", "esse modelo usa esse conceito AI".

### NÃO sinalize

- Status do dia / o que acabou de fazer ("rodei pytest, passou", "rebasei na main").
- Refactors triviais, fixes de typo, renames mecânicos.
- Coisas claras lendo o código (docstrings já cobrem; vault não duplica).
- Reformulações de info já presente no vault sem novo insight.

## Não-captura (regras absolutas)

**Nunca capturar no vault, mesmo se aparecer na conversa**:

- Credenciais, senhas, chaves API, tokens, `webhook_secret` real.
- Strings de conexão completas com password.
- Dados pessoais de pacientes ou médicos (CPF, telefone, endereço).
- Valores comerciais cliente-específicos (preço cobrado da Clínica X).
- Conteúdo de `.env`, certificados, secrets.

Se o usuário pedir explicitamente pra capturar algo dessas categorias, **recusar** e explicar o motivo. Vault vai pra GitHub junto com o código — privado != seguro pra credencial.

## Dedup obrigatório no `/capture`

**Antes de escrever nota nova**, sempre:

1. `Grep` no vault pelo termo principal (nome de entidade, palavra-chave do tópico).
2. `Read` das ~3 notas mais relevantes encontradas.
3. Decidir:
   - Já existe nota cobrindo o tópico → **propor update da nota existente** (diff explícito), não criar nova.
   - Tópico relacionado mas distinto → **criar nova com link `[[...]]`** pra existente.
   - Nada relacionado → criar nova.

Vault duplicado é vault morto.

## Leitura: regra `Grep`-first

Quando trabalhando neste repo, **antes de responder** sobre:

- Entidade do domínio nominada (`Clinica`, `Paciente`, `Agendamento`, `Conversa`, ...).
- Tag/ID de domínio ou setting (`clinica_id`, `app.clinica_id`, RLS, `BYPASSRLS`, `webhook_secret`).
- Integração específica (Evolution API, WhatsApp Cloud API, Anthropic SDK, OpenRouter, Langfuse).
- Fluxo de conversação (agendar, remarcar, cancelar, lembrete, handoff).
- Conceito AI usado no produto (prompt caching, tool use, evals, RAG, agentic loop).

→ **`Grep` no `vault/` primeiro**. Se encontrar, ler antes de responder. Citar a nota usada na resposta (ajuda usuário a auditar e atualizar).

## Convivência com `docs/`

| Conteúdo | Onde mora |
|---|---|
| Pedagogia longa estilo livro técnico (RLS deep dive, prompt caching deep dive) | [`docs/ai-engineering/`](../docs/ai-engineering/) |
| Decisão arquitetural grande com tradeoffs alternativos formais | [`docs/adr/`](../docs/adr/) |
| Plano de fase do projeto | [`docs/plans/`](../docs/plans/) |
| Contexto público macro (produto, stack, decisões MVP, histórico) | [`docs/context/`](../docs/context/) |
| Nota atômica por entidade/conceito/integração/fluxo | `vault/` |
| Aprendizados evolutivos | `vault/aprendizados/` |
| Diário de sessões | `vault/diario/` |

`vault/conceitos-ai/<x>.md` é nota curta com link pra `docs/ai-engineering/<x>.md` quando vira deep dive. Sem duplicação de conteúdo.

## Re-revisão manual

Sem TTL automático. Quando alguém (humano ou Claude) ler uma nota e perceber que tá velha:

1. Avisar no chat: *"a nota `vault/<path>` parece desatualizada porque <motivo>. Quer atualizar?"*.
2. Se sim: propor diff e atualizar.
3. Se não: deixar como está. Stale conhecido > stale escondido.

`git log -- vault/<path>` mostra quando foi escrita/atualizada por último — use como heurística de "essa info é de quando?".
