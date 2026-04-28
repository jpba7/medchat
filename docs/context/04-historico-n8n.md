---
name: Workflow MedChat atual
description: Estado e problemas do workflow MedChat existente (ID 0O13PjgBKcONHd0F) em 2026-04-17 — sandbox, pode ser refeito.
type: project
originSessionId: 75279bca-61cb-467e-9eb0-e13093a19b81
---
**Workflow existente em 2026-04-17:** `MedChat` (ID `0O13PjgBKcONHd0F`), 101 nodes, 64 conexões, ativo, sandbox (sem pacientes reais).

**Contexto errado:** O prompt do agente foi desenhado como bot de vendas B2B ("Igor Miguel / Grupo Nexus Mind" pitchando IA para clínicas), não como secretária virtual para pacientes. Arquitetura inteira precisa ser reescrita.

**Principais problemas do workflow atual:**
- Tool `agendamento` (workflowId `z0R0aP14vMrDmzad`) está desativada, mas o prompt manda usá-la — bot alucinaria horários
- `Error Trigger → Notifica Erro` só seta variáveis, não notifica ninguém (viola regra do CLAUDE.md)
- Áudio, imagem, PDF, RAG/Pinecone — todos nodes desativados (esqueletos de funcionalidades)
- Comando `/deletar` sem autenticação: qualquer telefone pode apagar a tabela Postgres de memória
- Cadastro mínimo (só telefone + nome via `pushName`); nada de email, CPF, convênio, LGPD
- Hardcoded `evolution_account_name = "projeto"` — nenhuma lógica multi-tenant
- Memória duplicada (Postgres Chat Memory + Redis `Get Memory 1/4/5/6/7`) — lógica confusa
- Debounce de 7 segundos agrupa mensagens (padrão 2026 é 3-5s)
- Nodes mortos: `AGRUPA MENSAGENS1`, `output mensagem1`, múltiplos `Get Memory` desativados

**Decisão:** Rasgar e refazer com arquitetura modular (sub-workflows). Workflow atual fica só como referência histórica.

**Why:** O workflow mistura experimentos de múltiplas fases (comercial B2B + tentativas de áudio/imagem/RAG) sem coerência. Refazer é mais rápido do que corrigir cada ponto.

**How to apply:** Não editar o workflow 0O13PjgBKcONHd0F incrementalmente. Criar novos workflows limpos seguindo a arquitetura modular acordada. Só preservar lógicas específicas que fizerem sentido (ex.: padrão de debounce com Redis, agrupamento de mensagens com `summarize`).
