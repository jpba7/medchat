---
name: agendar-consulta
type: fluxo
tags: [fluxo-principal, agendamento]
---

# Fluxo: Agendar consulta

> Fluxo principal do MedChat. Paciente manda mensagem no WhatsApp pedindo consulta → bot interpreta + sugere → confirma agendamento → grava + envia confirmação. Quando incerto, escala pra humano.
>
> ⚠️ **Schema do fluxo está pronto** (Item 7 da Fase 1 fechado: 14 tabelas tenant-aware + 40 testes verdes). **Comportamento do bot** ainda é Fase 2 — `apps/bot/` continua vazio.

## Disparado por

- Paciente manda mensagem no canal WhatsApp da clínica.
- Webhook da Evolution chega em `POST /api/webhooks/whatsapp/<canal_id>` (endpoint a criar — item 8 da Fase 1).

## Estados / etapas

1. **Webhook recebido**
   - Validação HMAC com `ClinicaCanal.webhook_secret`.
   - Resolução do tenant (`clinica` via FK do `ClinicaCanal`) — `RLSMiddleware` seta `app.clinica_id`.
   - Dedup via constraint `UNIQUE (canal_id, external_id) WHERE external_id IS NOT NULL` em `mensagens` (ver [[conceitos-ai/idempotencia-via-unique-parcial]]).
   - INSERT `Mensagem` (direção=`entrada`).

2. **Resolver `Paciente`**
   - Por `(clinica_id, telefone_e164)`. Cria se não existir, com `nome` do `pushName` do WhatsApp.
   - Se `lgpd_aceito_em IS NULL`, fluxo paralelo: bot apresenta `lgpd_texto` e bloqueia o resto até aceite.

3. **Atribuir / criar `Conversa`**
   - Procura `Conversa` ativa do paciente naquele canal (`status != 'encerrada'`). Se não existe, cria com `status='bot'`.

4. **Bot interpreta intenção**
   - Anthropic SDK ([[conceitos-ai/anthropic-sdk]]) — Sonnet 4.6 default.
   - Sistema-prompt traz `ClinicaPolitica` e contexto da clínica (prompt caching ajuda aqui).
   - Tool calls: `consultar_agenda(medico_id, data)`, `consultar_medicos(especialidade_id)`, `marcar_agendamento(...)`, etc.
   - Estado de slot fillers vai em `Conversa.contexto` JSONB.

5. **Sugestão de horários**
   - Bot consulta `MedicoDisponibilidade` + `Agendamento` ativos pra calcular slots livres.
   - Apresenta opções pro paciente (no máximo N).

6. **Confirmação**
   - Paciente escolhe slot. Mais mensagens trocadas se precisar mudar.

7. **Persistência (`Agendamento`)**
   - INSERT com `status='agendado'`. **`EXCLUDE USING GIST` no banco rejeita** se outro agendamento ATIVO do mesmo `medico_id` se sobrepuser ([[conceitos-ai/exclude-using-gist]]).
   - `clean()` valida cross-tenant: `paciente`, `medico`, `convenio` precisam ter mesmo `clinica_id`.

8. **Outbox de confirmação**
   - INSERT `Mensagem` (direção=`saida`, `external_id=NULL`).
   - INSERT `Outbox` (`tipo='whatsapp_text'`, `payload={to_e164, body, mensagem_id}`, `status='pendente'`).
   - Retorno do request: 200 OK em ms.
   - Em paralelo, Celery `send_outbox` task envia, atualiza `Mensagem.external_id` ([[conceitos-ai/outbox-pattern]]).

9. **Eventos**
   - `EventoBot` registra `mensagem_recebida` (passo 1), `tool_call` (passo 4), `resposta_enviada` (passo 8) — pro painel da clínica.

## Decisões pelo bot vs handoff humano

- **Bot resolve sozinho quando**: intenção clara, paciente conhecido, slot livre disponível dentro do horário comercial.
- **Escala pra humano (`Handoff`) quando**:
  - `gatilho='pedido_explicito'` — paciente pediu pessoa.
  - `gatilho='confianca_baixa'` — bot incerto sobre intenção.
  - `gatilho='urgencia_medica'` — palavras-chave de urgência detectadas.
  - `gatilho='reclamacao'` — detector de reclamação ativou.
- **Bot não escala** fora do `ClinicaPolitica.horario_handoff_humano` — responde sozinho com aviso "atendente disponível em [próximo horário]".

`Conversa.status` reflete: `bot` → `handoff_aguardando` → `handoff_ativo` → `bot` (atendente termina) ou `encerrada`.

## Entidades envolvidas

- [[entidades/clinica]] — tenant + `ClinicaCanal` + `ClinicaPolitica`
- [[entidades/paciente]] — resolvido na primeira mensagem
- [[entidades/catalog]] — `Especialidade`, `Medico`, `Convenio`, `MedicoConvenio`, `MedicoDisponibilidade`
- [[entidades/agendamento]] — criado no passo 7
- [[entidades/conversations]] — `Conversa`, `Mensagem`, `Handoff`
- [[entidades/outbox]] — `Outbox` (envio) + `EventoBot` (log)

## Integrações envolvidas

- [[integracoes/evolution-api]] — canal WhatsApp (inbound webhook + outbound send)

## Conceitos AI / arquitetura usados

- [[conceitos-ai/anthropic-sdk]] — provedor LLM
- [[conceitos-ai/exclude-using-gist]] — anti-overlap de agendamento
- [[conceitos-ai/outbox-pattern]] — envio assíncrono
- [[conceitos-ai/idempotencia-via-unique-parcial]] — dedup de webhook

## Políticas configuráveis (`ClinicaPolitica`)

- `cancelamento_antecedencia_h` — janela mínima pra cancelar (afeta confirmação)
- `cpf_obrigatorio` — exige CPF antes de marcar
- `lgpd_texto` — apresentado ao paciente novo até `Paciente.lgpd_aceito_em` ser preenchido
- `lembrete_janelas_h` — quando disparar lembretes (ex.: `[24, 2]` h antes)
- `saudacao_bot` — primeira frase ao paciente novo
- `horario_handoff_humano` — quando bot pode escalar pra humano

## Gotchas / edge cases

- **Janela de 24h do WhatsApp Business**: fora dela, só template aprovado. Lembretes precisam ser template; conversa rolando dentro da janela pode ser texto livre. `Outbox.tipo='whatsapp_template'` pra esses casos.
- **Paciente novo vs retornante**: identificação por `(clinica_id, telefone_e164)`. Mesmo número pode ter mais de um paciente atrelado (filho, cônjuge) — definir como tratar quando aparecer caso real.
- **Mensagem duplicada do provedor**: dedup pelo constraint parcial. Se passar dedup, é bug.
- **`Clinica.ativa = False`**: webhook entra (responde 200) mas tasks não disparam. Bot fica mudo do ponto de vista do paciente. Soft-disable.
- **Race em slot livre**: `EXCLUDE USING GIST` rejeita o segundo INSERT. Bot precisa tratar `IntegrityError` e oferecer outro horário.
- **CPF obrigatório com paciente sem CPF**: bot precisa pedir antes de tentar marcar. Estado em `Conversa.contexto` rastreia o que falta.

## Próximos passos (Fase 2)

- Implementar handler do webhook em `apps/channels/` (item 8 da Fase 1).
- `config/celery.py` (item 9 da Fase 1) — pré-requisito pro `send_outbox`.
- Sistema-prompt do bot (`apps/bot/`) com regras da clínica + tools.
- Tools concretas: `consultar_agenda`, `consultar_medicos`, `marcar_agendamento`, `cancelar_agendamento`, `escalar_humano`.
- Detector de urgência médica + reclamação (heurísticas + LLM).
