---
name: Decisões MedChat MVP
description: Escopo do MVP, handoff humano, LGPD, identificação de paciente e políticas da secretária virtual.
type: project
originSessionId: 75279bca-61cb-467e-9eb0-e13093a19b81
---
**Decisões fechadas em 2026-04-17:**

**Escopo MVP (dia 1):**
- Agendar consulta (guiado: especialidade → médico → convênio → horário)
- Remarcar consulta
- Cancelar consulta
- Lembretes automáticos configuráveis por clínica (cobrem toda a agenda, inclusive agendamentos feitos fora do bot pela secretária humana)

**Identidade do bot:**
- Declara ser IA desde a primeira mensagem: "sou a assistente virtual da Clínica X"
- Nome/tom configuráveis por clínica (no painel Django)

**Identificação do paciente:**
- Telefone (WhatsApp) + nome completo são obrigatórios
- CPF é opcional e configurável pela clínica (cada cliente decide se pede)

**LGPD:**
- Aviso curto + aceite implícito por uso continuado na primeira interação
- Mensagem padrão: "Ao continuar, você concorda com o tratamento dos seus dados. Detalhes em [link]"

**Handoff humano (4 gatilhos):**
1. Paciente pedir explicitamente falar com atendente
2. Baixa confiança da IA (pergunta fora do FAQ/escopo)
3. Palavras-chave de urgência médica (dor no peito, sangramento, desmaio etc) — bot também orienta 192/SAMU
4. Reclamação, tópico sensível ou após N falhas de entendimento

**Canal de handoff:**
- Painel web (Django) com inbox + badge de não lidas
- + Notificação por WhatsApp no número do atendente da clínica

**Horário de atendimento:**
- Bot 24/7
- Handoff humano só em horário comercial configurado pela clínica
- Fora de horário: bot responde "nossa equipe retorna amanhã às 8h"

**Multimodalidade:** Só texto no MVP. Se paciente mandar áudio/imagem/PDF, bot pede para escrever.

**Políticas de cancelamento/remarcação:** Configuráveis no painel por clínica (prazo mínimo, máximo de remarcações). Após o prazo, bot escala para humano avaliar.

**Why:** Escopo enxuto para validar produto sem abrir muitos flancos. Multimodalidade, triagem clínica e pagamentos ficam para v2 — aumentariam risco regulatório (LGPD Art. 11, CFM) e complexidade.

**How to apply:** Qualquer nova feature deve ser checada contra esse escopo. Se fugir (ex.: "bot responde dúvida sobre medicamento"), escalar para humano, não inventar. Toda regra de política (prazos, horários, identificação) lê do painel (Supabase), nunca hardcoded.
