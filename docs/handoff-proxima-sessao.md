# Prompt para retomar o projeto em nova sessão Claude Code

Cole o conteúdo abaixo no início de uma nova sessão Claude Code aberta dentro de `C:\Repos\medchat`.

---

```text
Estou continuando o projeto MedChat numa nova sessão Claude Code. Working dir: C:\Repos\medchat.

PRODUTO: SaaS B2B de secretária virtual com IA para clínicas médicas. Multi-tenant, WhatsApp como canal primário, agendamento + lembretes + handoff humano. Stack Django + Postgres (RLS) + Celery + Anthropic SDK + Langfuse.

ANTES DE FAZER QUALQUER COISA, LEIA EM ORDEM:
1. README.md
2. docs/context/01-produto.md
3. docs/context/02-stack.md
4. docs/context/03-decisoes-mvp.md
5. docs/context/04-historico-n8n.md
6. docs/plans/01-fundacao-fase-1.md (plano completo aprovado: schema, estrutura, passo-a-passo, riscos, critérios de conclusão)

ESTILO DE TRABALHO (importante):
Sou iniciante em AI Engineering, uso Claude Code, mirando empregabilidade. Quero aprender enquanto construo.

A cada passo grande:
1. Você executa (uv add X, criar arquivo Y, rodar comando Z)
2. Mostra output real e arquivos criados
3. Explica o conceito em 4-6 linhas: o que é, por que estamos usando, alternativas, link pra aprofundar
4. Pergunta se tenho dúvidas antes de seguir

Para cada feature AI nova (LLM, prompt caching, tool use, RAG), antes de implementar, escreva um .md em docs/ai-engineering/ com: conceito, por que usamos no MedChat, como funciona, referências externas. Os 7 fundacionais estão listados no plano.

Para cada decisão arquitetural significativa, registre um ADR em docs/adr/.

Comentários, docs, mensagens do bot e mensagens de commit em português brasileiro.

ESTADO ATUAL:
- git init -b main feito
- docs/{context,adr,ai-engineering,plans}/ criados
- uv init --bare (pyproject.toml mínimo)
- .python-version = 3.13
- README.md e .gitignore prontos
- Plano + 4 docs de context já copiados

Pré-requisitos verificados: Python 3.13.13, uv 0.11.8, Docker 29.2.1, Docker Compose 5.0.2, git 2.47.

Nada de Django, dependências, apps, Docker stack, modelos ou migrations criado ainda. Pasta n8n-automations antiga fica intocada como referência.

PRÓXIMO PASSO:
Passo 1 do plano: adicionar dependências via uv add. Lista no plano (seção "Passo-a-passo de execução"). Depois disso vem Django scaffold (passo 2), apps (passo 3), Docker Compose (passo 4) etc.

Pause depois de uv add e me explique cada uma das principais (Django, Ninja, psycopg, Celery, anthropic, langfuse, django-pgtrigger).

CONSTRAINTS:
1. Multi-tenant RLS desde o dia 1 — toda tabela tenant-owned tem clinica_id + policy Postgres + middleware seta app.clinica_id por request.
2. Sem LLM nesta fase — só infra. Webhook ecoa "Recebi. Em instantes respondo." Fase 2 traz o agente.
3. Idempotência de webhook via unique (canal_id, external_id).
4. Outbox pattern pra envio WhatsApp.
5. Pergunte antes de assumir — se algo for ambíguo, perguntar.
6. Use o `uv` instalado em C:\Users\peedr\.local\bin (já está no PATH, mas se a sessão nova não enxergar, usar caminho absoluto).

Comece lendo os docs e depois execute o próximo passo com pausa pedagógica.
```

---

## Como usar

1. Abra uma nova sessão do Claude Code em `C:\Repos\medchat\` (ex.: VS Code → Claude Code → "Open in folder").
2. Cole o bloco entre as aspas triplas como sua primeira mensagem.
3. O Claude vai ler os docs apontados e começar do passo 1 (uv add).

## Quando atualizar este prompt

Toda vez que você terminar uma fase ou um marco grande:
- Atualize a seção `ESTADO ATUAL` (o que já foi feito)
- Atualize a seção `PRÓXIMO PASSO`
- Mantenha o resto igual

Pra projetos longos, vale ter `docs/handoff-proxima-sessao.md` versionado e atualizado a cada PR mergeado, funciona como cabeçalho de onboarding pro próximo dev (humano ou IA).
