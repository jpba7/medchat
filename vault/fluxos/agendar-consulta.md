---
name: agendar-consulta
type: fluxo
tags: [skeleton, fluxo-principal]
---

# Fluxo: Agendar consulta

> ⚠️ **Skeleton.** Os apps `appointments`, `patients`, `bot`, `conversations` ainda estão vazios na Fase 1. Esta nota é placeholder estrutural — vai ser preenchida conforme o código aparece.

> Fluxo principal do MedChat: paciente manda mensagem no WhatsApp pedindo consulta → bot conversa → confirma agendamento → grava no banco da clínica → manda confirmação. Quando o bot não tem certeza, escala pra humano.

## Disparado por

- Paciente manda mensagem nova no canal WhatsApp da clínica.
- Webhook da Evolution chega em `POST /webhooks/evolution/<canal>`.

## Estados / etapas (rascunho)

1. **Webhook recebido** — HMAC validado, dedup por `(canal_id, external_id)`, mensagem persistida.
2. **Pré-coleta** — bot identifica intenção (agendar?), pede dados faltantes (nome, especialidade, CPF se `cpf_obrigatorio` na `ClinicaPolitica`).
3. **Sugestão de horários** — bot consulta agenda da clínica → propõe slots livres.
4. **Confirmação** — paciente escolhe slot.
5. **Persistência** — `Agendamento` criado (entidade ainda não existe).
6. **Outbox de confirmação** — mensagem de confirmação gravada em `outbox` → Celery envia.

## Decisões pelo bot vs handoff humano

- **Bot resolve sozinho quando**: intenção clara, dados completos, slot livre disponível.
- **Escala pra humano quando**: incerteza alta, conflito de agenda, paciente pede falar com pessoa, fora do `horario_handoff_humano` da `ClinicaPolitica`.

(A definir critérios concretos quando `apps/bot/` ganhar código.)

## Entidades envolvidas

- [[entidades/clinica]] — tenant + `ClinicaCanal` + `ClinicaPolitica`
- (futuras) `Paciente`, `Medico`, `Agendamento`, `Conversa`, `Mensagem` — apps existem como scaffold, modelos vazios.

## Integrações envolvidas

- [[integracoes/evolution-api]] — canal WhatsApp (inbound + outbound)
- (futura) Anthropic SDK — interpretação e geração de resposta

## Conceitos AI usados

- [[conceitos-ai/anthropic-sdk]] — provedor LLM
- (futuras) prompt-caching, tool-use, evals

## Políticas configuráveis (`ClinicaPolitica`)

- `cancelamento_antecedencia_h` — janela mínima pra cancelar (afeta confirmação)
- `cpf_obrigatorio` — exige CPF antes de marcar
- `saudacao_bot` — primeira frase ao paciente novo
- `horario_handoff_humano` — quando bot pode escalar pra humano

## Gotchas / edge cases

- **Janela de 24h do WhatsApp Business**: fora dela, só template aprovado. Lembretes precisam ser template; conversa rolando dentro da janela pode ser texto livre.
- **Paciente novo vs retornante**: identificação por número E.164 + (futuramente) CPF. Mesmo número pode ter mais de um paciente atrelado (filho, cônjuge).
- **Mensagem duplicada do provedor**: dedup por `external_id`. Se passar dedup, é bug.
- **Clínica `ativa = False`**: webhook entra (responde 200) mas tasks não disparam. Bot fica mudo do ponto de vista do paciente. Documentar essa decisão melhor quando aparecer feature.

## Próximos passos

Quando os modelos de domínio começarem a sair (provável próxima parte da Fase 1):

- Atualizar a seção "Estados / etapas" com os nomes reais de classes/funções.
- Linkar entidades novas: `[[entidades/paciente]]`, `[[entidades/agendamento]]`, `[[entidades/conversa]]`.
- Criar nota `[[conceitos-ai/tool-use]]` quando o bot ganhar tool calling.
