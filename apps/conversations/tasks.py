"""Tasks Celery do app `conversations`.

`process_inbound_message` é o entrypoint pós-webhook: o handler
HTTP grava `Mensagem` (direção entrada) e enfileira esta task,
que faz o trabalho pesado fora do request — gera a resposta do
bot e enfileira no `Outbox`.

Na Fase 1 a resposta é o eco MVP estático ("Recebi. Em
instantes respondo."). Fase 2 substitui por chamada Anthropic +
prompt da clínica.
"""

from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from apps.core.tenancy import with_tenant

from .models import Conversa, Mensagem

ECO_MVP = "Recebi. Em instantes respondo."


@shared_task
@with_tenant
def process_inbound_message(*, clinica_id, mensagem_id):
    """Processa uma mensagem recebida do paciente.

    Fluxo Fase 1:
    1. Carrega `Mensagem` de entrada (já gravada pelo webhook handler).
    2. Atualiza `Conversa.atualizado_em` (sinal de atividade pra inbox).
    3. Cria `Mensagem` de saída com o eco MVP.
    4. Insere linha no `Outbox` apontando pra essa mensagem (a task
       `send_outbox` resolve o envio real).

    `task_id=mensagem_id` (passado pelo caller no webhook handler)
    dá idempotência adicional via Celery — se o webhook reentrega,
    o broker descarta a 2ª tentativa pelo mesmo `task_id`. Constraint
    no banco ainda protege caso essa camada falhe.
    """
    # Imports locais para evitar circular (Outbox vive em channels).
    from apps.channels.models import Outbox

    entrada = Mensagem.objects.select_related("conversa").get(id=mensagem_id)

    conversa: Conversa = entrada.conversa
    conversa.atualizado_em = timezone.now()
    conversa.save(update_fields=["atualizado_em"])

    saida = Mensagem.objects.create(
        conversa=conversa,
        canal=conversa.canal,
        direcao=Mensagem.Direcao.SAIDA,
        remetente="bot",
        conteudo=ECO_MVP,
        # external_id NULL — provedor preenche quando `send_outbox`
        # confirmar entrega (Fase 1 item 10).
        external_id=None,
    )

    Outbox.objects.create(
        clinica=conversa.clinica,
        tipo=Outbox.Tipo.WHATSAPP_TEXT,
        payload={
            "to_e164": entrada.remetente,
            "body": ECO_MVP,
            "mensagem_id": str(saida.id),
            "conversa_id": str(conversa.id),
        },
        proxima_em=timezone.now(),
    )
    return str(saida.id)
