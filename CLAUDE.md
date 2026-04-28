# MedChat — instruções do projeto

> Este arquivo é auto-carregado pelo Claude Code em toda sessão deste repositório. Mantém regras, contexto e convenções vivas.

## O que é o MedChat

SaaS B2B multi-tenant. Vendemos para clínicas médicas. Em cada clínica, o produto opera como **secretária virtual com IA** que conversa com pacientes via WhatsApp — agenda, remarca, cancela consultas e dispara lembretes. Quando incerta, escala para humano.

- **Cliente pagante:** clínica (B2B)
- **Usuário final:** paciente (B2C, via WhatsApp)
- **Multi-tenant** desde o dia 1, isolamento por `clinica_id` com Row-Level Security do Postgres
- **Bot declara ser IA** ("sou a assistente virtual da Clínica X"), nunca finge ser humano

Detalhes em [`docs/context/`](docs/context/).

## Status atual

**Fase 1 — Fundação.** Plano aprovado em [`docs/plans/01-fundacao-fase-1.md`](docs/plans/01-fundacao-fase-1.md). Progresso atual em [`docs/context/05-progresso-fase-1.md`](docs/context/05-progresso-fase-1.md).

## Stack confirmada (imutável na Fase 1)

| Camada | Escolha |
|---|---|
| Linguagem/gerenciador | Python 3.13 + `uv` |
| Web | Django 5 + Django Ninja |
| Banco | Postgres 17 com `pgvector`, RLS multi-tenant |
| Cache/broker | Redis 7 |
| Async | Celery + Celery Beat |
| LLM | Anthropic SDK (principal) + OpenRouter (fallback) |
| Obs AI | Langfuse self-hosted |
| Canal WhatsApp | Evolution API (MVP) → WhatsApp Cloud API (produção) |
| Deploy | Railway |
| Testes | pytest + pytest-django + factory-boy |
| Lint | ruff |

## Ordem de leitura ao iniciar uma sessão nova

1. Este `CLAUDE.md`
2. [`docs/context/05-progresso-fase-1.md`](docs/context/05-progresso-fase-1.md) — onde paramos
3. [`docs/plans/01-fundacao-fase-1.md`](docs/plans/01-fundacao-fase-1.md) — plano da fase atual
4. [`docs/context/03-decisoes-mvp.md`](docs/context/03-decisoes-mvp.md) — decisões fechadas que não se rediscutem
5. ADR(s) recém-criadas em `docs/adr/` (se houver)

## Regras obrigatórias

1. **RLS em toda query tenant-aware.** Antes de criar/ler qualquer modelo com `clinica_id`, garanta que `app.clinica_id` está setado na transação. Se não estiver, falhe alto (500), nunca silencie.
2. **Migrations testáveis.** Cada PR com migration roda contra um Postgres real (docker-compose). Nunca squashar, nunca editar migration aplicada — gerar nova.
3. **Webhook idempotente.** Toda mensagem entra com `external_id` único; `(canal_id, external_id)` é unique constraint. Se vier repetida, deduplica.
4. **Outbox pattern para envio externo.** Nunca chamar Evolution/Cloud API direto do request — gravar em `outbox` e deixar Celery enviar.
5. **Erro estruturado.** Nada de `except: pass`. Loggar `clinica_id`, `conversa_id`, contexto. Sentry-ready.
6. **Snake_case** em modelos, colunas e arquivos Python. Nomes de domínio em **pt-BR** (`agendamento`, `medico`, `paciente`) — produto é Brasil-first.
7. **Antes de cada feature AI** novo, criar um `.md` curto em `docs/ai-engineering/` explicando conceito + por que usamos + como funciona + links externos. Documentar antes ou junto, nunca depois.
8. **Decisões arquiteturais grandes** geram um ADR em `docs/adr/NNNN-titulo.md`. Imutável depois de aceito.
9. **Teste manual + automatizado antes de declarar pronto.** `make test` verde + smoke manual da feature.

## Estilo de trabalho com Claude

O usuário (dono do projeto) é **iniciante em AI Engineering** e quer aprender com profundidade enquanto constrói, mirando empregabilidade. Logo:

- A cada passo grande, **execute → mostre o resultado → explique o conceito** (4-6 linhas, com link externo) → pergunte se há dúvida antes de seguir.
- Não rode 5 comandos seguidos sem pausa pedagógica. Build verde silencioso ≠ aprendizado.
- Use `docs/ai-engineering/` como aprendizado profundo (consulta posterior). Pausas no chat são aprendizado just-in-time.
- Quando criar arquitetura nova, justifique o por quê + 1-2 alternativas descartadas, em 3 linhas.

## Estilo de commits e interação com git

Commits do MedChat são **material de aprendizado**, não só registro técnico. O `git log -p` deve poder ser lido daqui a 6 meses como um livro técnico do produto: cada commit conta uma parte da história *e* ensina o conceito por trás. Aplicar a TODA interação com git neste repo, sem exceção.

1. **Separar por unidade lógica.** Um commit = uma história coerente. Se o diff cobre dois conceitos diferentes (ex.: "scaffold inicial" + "primeiro modelo de domínio"), são dois commits — não bundle.
2. **Subject curto, em pt-BR**, com prefixo de tipo: `feat:`, `fix:`, `docs:`, `build:`, `ops:`, `chore:`, `refactor:`, `test:`. Máx ~70 chars. (Padrão Conventional Commits adaptado pra pt-BR — ver [conventionalcommits.org](https://www.conventionalcommits.org/pt-br/).)
3. **Body narrativo e pedagógico**, em 4 blocos rotulados:
   - **O quê:** o que esse commit muda no mundo (1-2 linhas).
   - **Por quê:** a motivação concreta + 1-2 alternativas que descartamos e por quê.
   - **Conceito:** 2-4 linhas ensinando o tema técnico subjacente (RLS, outbox pattern, prompt caching, tool use, etc) com link externo se útil.
   - **Próximo passo:** o que esse commit destrava na sequência.
4. **Commits curtos preferidos a commits gigantes.** Se a mensagem fica difícil de escrever, o passo é grande demais — split em commits menores.
5. **Sempre revisar `git diff --cached`** antes de commitar. Nunca `git add .` cego — preferir `git add <arquivo>` por nome para evitar sweepar segredos ou binários por engano.
6. **Nunca usar `--no-verify`** ou pular hooks. Se hook falha, fixar a causa.
7. **Mensagem via heredoc** pra preservar formatação multilinha.

## Comandos comuns

> ⚠️ Em construção — Fase 1 ainda não terminou. À medida que o `Makefile` for criado, os atalhos abaixo passam a funcionar:

```bash
# (Fase 1 vai entregar)
make up                # docker compose up -d
make down              # docker compose down
make migrate           # python manage.py migrate
make test              # pytest
make lint              # ruff check + format --check
make shell             # python manage.py shell_plus
make logs              # docker compose logs -f
```

Por enquanto, os equivalentes manuais:
```bash
uv add <pacote>                   # adicionar dependência
uv sync                           # sincronizar lockfile
uv run python manage.py <cmd>     # rodar comandos Django
uv run pytest                     # rodar testes
```

## Histórico

Este projeto começou como prova-de-conceito em n8n no diretório `C:\Users\peedr\n8n-automations\` (workflow `0O13PjgBKcONHd0F` na instância Cloudfy `unknownserval-n8n.cloudfy.live`). A revisão concluiu que Django+Postgres é o stack certo. O n8n original ficou intocado como referência.

## Memórias auto-carregadas

Path-scoped: `~/.claude/projects/C--Repos-medchat/memory/` (não criada ainda). Quando criar memórias durante o trabalho, salvar lá; o conteúdo `docs/context/` é a fonte de verdade pública versionada — memórias do Claude são notas operacionais privadas.
