---
name: anthropic-sdk
type: conceito-ai
tags: [llm, anthropic, sdk]
---

# Anthropic SDK

> Provedor LLM principal do MedChat. Toda interação do bot com modelos de linguagem passa pelo SDK oficial da Anthropic. Fallback é OpenRouter (mesma família de modelos quando indisponível).

## O que é

SDK Python oficial da Anthropic (`anthropic` no PyPI) pra chamar a API de modelos Claude. Fornece `messages.create()` (texto), tool use (function calling), prompt caching, batch API, e streaming.

## Por que usamos no MedChat

- **Estabilidade e qualidade** dos modelos Claude pra tarefa de conversação clínica em pt-BR.
- **Prompt caching nativo** — sistema-prompts longos (regras da clínica, políticas, estilo de voz) cacheados no servidor reduzem custo e latência das mensagens curtas do paciente.
- **Tool use** — bot decide chamar ferramenta (consultar agenda, marcar consulta, buscar paciente por CPF) em vez de tentar gerar resposta direta.

Alternativas descartadas:

- **OpenAI direto:** ficou como concorrente, não escolhido. Caso queira fallback multi-provedor, usar OpenRouter (já no plano).
- **Auto-hospedar Llama/Mistral via vLLM:** custo operacional alto pra time pequeno. Desconsiderado.

## Como aparece no código

- **App responsável:** `apps/bot/` (ainda vazio na Fase 1, scaffold só).
- **Env var esperada:** `ANTHROPIC_API_KEY` (em `.env`, não commitada).
- **Fallback:** `OPENROUTER_API_KEY` quando Anthropic indisponível.

## Modelo / SDK / biblioteca usada

Pacote: `anthropic` (PyPI). Modelos por caso de uso (escolha a confirmar conforme aparecer feature):

| Modelo | Caso de uso provável |
|---|---|
| **Claude Opus 4.7** | Raciocínio complexo (resolver caso ambíguo, decidir handoff) |
| **Claude Sonnet 4.6** | Default — conversa de agendamento, leitura de mensagem do paciente |
| **Claude Haiku 4.5** | Tarefas leves (triagem, lembretes, classificação simples) |

Decisão de modelo por caso de uso ainda não está fechada — vai ser tomada conforme cada feature do bot aparece. Manter aqui como referência.

## Gotchas

- **Cutoff de conhecimento** dos modelos não inclui regras específicas das clínicas — TODA política da clínica precisa estar no prompt (sistema ou user), nunca confiar que o modelo "sabe" como a clínica X opera.
- **Tool use ≠ execução**: o modelo decide chamar uma tool, mas é o **MedChat** que executa. O modelo só sugere; a aplicação valida (ex.: confirma slot livre antes de marcar).
- **Bot declara ser IA** — regra do CLAUDE.md. Sistema-prompt obriga a frase "sou a assistente virtual da Clínica X". Não fingir ser humano.
- **Prompt caching** funciona por bloco — cache hit em sistema-prompt longo só vale se o prefixo for idêntico byte-a-byte. Mudar uma linha invalida o cache.
- **Custo de Opus** — usar com parcimônia, só onde Sonnet falha. Bot de conversação rotineira fica com Sonnet.

## Notas relacionadas

- [[fluxos/agendar-consulta]] — usa o SDK pra interpretar mensagem e decidir tool calls
- (futuras) [[conceitos-ai/prompt-caching]], [[conceitos-ai/tool-use]], [[conceitos-ai/evals]]

## Deep dive

- (a criar) `docs/ai-engineering/<NN>-anthropic-sdk-medchat.md` — quando o app `apps/bot/` ganhar código, escrever pedagogia longa lá.

## Referências externas

- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Docs Claude API](https://docs.claude.com/en/api/overview)
- [Prompt caching](https://docs.claude.com/en/docs/build-with-claude/prompt-caching)
- [Tool use](https://docs.claude.com/en/docs/build-with-claude/tool-use)
- [OpenRouter](https://openrouter.ai/) — fallback multi-provedor.
