---
description: Captura candidatos do vault sinalizados na sessão (batch, com aprovação humana)
---

# /capture — Captura batch pro vault

Você está rodando o comando `/capture`. Este comando coleta tudo que foi sinalizado como candidato a virar nota no `vault/` durante a sessão atual e propõe ao usuário, com aprovação por item, antes de escrever qualquer arquivo.

**Regras de operação completas em [`vault/README.md`](../../vault/README.md). Ler antes de prosseguir se este é seu primeiro `/capture` da sessão.**

## Passo 1 — Coletar candidatos

Releia esta sessão e liste todos os pontos onde você (Claude) sinalizou:

```
💡 vault candidate: <descrição curta>
```

Se não houver nenhum, responda: *"Nenhum candidato sinalizado nesta sessão. Vault não muda."* e pare. Não invente candidatos retroativamente.

## Passo 2 — Filtro vault-worthy (auto-revisão)

Pra cada candidato coletado, confirme que atende **pelo menos um**:

- Conhecimento de domínio com motivo (regra de negócio, decisão pequena com porquê).
- Detalhe operacional não-óbvio (gotcha, workaround, restrição escondida).
- Conexão entre entidades já existentes no vault.

Descarte (silenciosamente, mas mostre na resposta o que foi descartado e por quê):

- Status do dia / atividade ("rodei pytest").
- Refactor trivial, fix de typo.
- Coisas claras lendo o código.
- Reformulação de info já no vault.

## Passo 3 — Bloqueio absoluto

Se algum candidato envolve **qualquer** dos itens abaixo, **descartar** e avisar:

- Credencial, senha, chave API, token, `webhook_secret` real.
- String de conexão completa com password.
- Dado pessoal de paciente ou médico (CPF, telefone, endereço).
- Valor comercial cliente-específico.
- Conteúdo de `.env`, certificado, secret.

Se o usuário insistir em capturar item bloqueado, recusar e explicar: vault vai pra GitHub junto com código — privado != seguro pra credencial.

## Passo 4 — Dedup obrigatório

Pra cada candidato sobrevivente:

1. `Grep` no `vault/` pelo termo principal (nome de entidade, palavra-chave do tópico). Use `output_mode: "files_with_matches"` primeiro.
2. Se houver matches: `Read` das ~3 notas mais relevantes.
3. Decida o destino:
   - **Já existe nota cobrindo o tópico** → propor **update** da nota existente. Mostre diff explícito do bloco que muda.
   - **Tópico relacionado mas distinto** → propor **nova nota** com link `[[...]]` pra existente.
   - **Nada relacionado** → propor **nova nota** do zero.

## Passo 5 — Apresentar proposta ao usuário

Pra cada candidato (numerado), mostre:

```
=== Candidato N ===
Origem: <citação curta da conversa de onde veio>
Destino proposto: NOVA nota | UPDATE de [[<path>]]
Path: vault/<categoria>/<slug>.md
Tipo: <type>

— Conteúdo proposto:
<o conteúdo da nota nova OU o diff do update>

Aprovar? (sim / não / editar)
```

Liste tudo. **Não escreva nada ainda.** Espere o usuário responder.

## Passo 6 — Escrever só o que foi aprovado

Pra cada candidato com aprovação `sim`:

1. Use o template apropriado em `vault/_templates/` como base estrutural (não copie literal — preencha).
2. Frontmatter mínimo: `title`, `type`, `tags` (opcional). **Sempre `title:`, nunca `name:`** — `title` é o campo canônico do Obsidian que renderiza o nome no graph view.
3. Linguagem: pt-BR pra narrativa, identifiers preservados, termos de domínio em pt-BR.
4. Use `Write` (nota nova) ou `Edit` (update).
5. Atualize [`vault/MOC.md`](../../vault/MOC.md) se houver nota nova — adicione linha na seção apropriada.

Pra `editar`: pergunte ao usuário o que mudar e re-apresente. Pra `não`: descarte silenciosamente.

## Passo 7 — Reportar

Resposta final com:

- Notas criadas: lista com paths.
- Notas atualizadas: lista com paths.
- Candidatos descartados (e motivo curto).
- `MOC.md` atualizado? sim/não.

## Erros comuns a evitar

- **Não criar nota duplicada** — sempre dedup primeiro.
- **Não escrever inline durante a sessão** — só sinalizar. `/capture` é o único lugar que escreve no vault.
- **Não capturar credencial nem PII** — mesmo se o usuário pedir.
- **Não inventar candidatos** — só captura o que foi explicitamente sinalizado com `💡 vault candidate:` durante a sessão.
- **Não reformular informação já presente sem novo insight** — descarte.
