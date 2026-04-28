---
name: Produto MedChat
description: O que é o produto MedChat, quem paga, quem usa e qual o contexto comercial.
type: project
originSessionId: 75279bca-61cb-467e-9eb0-e13093a19b81
---
**Produto:** SaaS B2B chamado MedChat. Vende secretária virtual com IA para clínicas médicas.

**Modelo de negócio:**
- Cliente pagante: clínica médica (B2B)
- Usuário final: paciente da clínica (B2C), que conversa com o bot
- Multi-tenant: cada clínica tem seus dados isolados por `clinica_id`
- Produto complementar: painel web (Django, projeto separado) onde a clínica gerencia médicos, horários, convênios, FAQ, políticas, inbox de conversas escaladas

**Why:** O workflow inicial confundia dois projetos (um bot de vendas "Igor Miguel / Grupo Nexus Mind" estava montado dentro do que deveria ser a secretária virtual). O projeto real é a secretária virtual; o bot de vendas, se existir, é outro workflow.

**How to apply:** Qualquer sugestão para o MedChat deve pensar em: (1) como a clínica cadastra/consome dados via Django, (2) como o paciente tem uma experiência conversacional boa no WhatsApp, (3) isolamento multi-tenant por `clinica_id` em todas as queries. Nunca misturar bot de vendas com o bot de atendimento ao paciente.
