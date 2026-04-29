"""Testes de integração das Celery tasks da Fase 1.

Roda com `CELERY_TASK_ALWAYS_EAGER=True` (configurado em
`config/settings/test.py`), então `task.delay(...)` executa
inline no processo de teste — sem broker, sem worker, sem
fila. Isso testa o **corpo** da task; testes que precisam
exercitar o roteamento via Redis ficariam para uma camada
acima (e não cabem na Fase 1).

Cobre:
- `process_inbound_message`: fluxo eco MVP completo
  (entrada → atualiza Conversa → cria saída → enfileira Outbox).
- `send_outbox`: transição `pendente → enviado` com timestamp.
- `send_outbox`: idempotência (chamada extra é no-op).
"""

from __future__ import annotations

import pytest
from django.utils import timezone

from apps.channels.models import Outbox
from apps.channels.tasks import send_outbox
from apps.clinics.models import ClinicaCanal
from apps.conversations.models import Conversa, Mensagem
from apps.conversations.tasks import ECO_MVP, process_inbound_message
from apps.core.tenancy import tenant_session
from apps.patients.models import Paciente


def _setup_conversa(clinica):
    """Cria paciente + canal + conversa mínimos. Sessão Postgres
    deve estar com `app.clinica_id` setado para a clínica dada."""
    paciente = Paciente.objects.create(
        clinica=clinica, telefone_e164="+5511999111111", nome="Carlos"
    )
    canal = ClinicaCanal.objects.create(
        clinica=clinica,
        tipo=ClinicaCanal.Tipo.WHATSAPP_EVOLUTION,
        numero_e164="+5511222000111",
    )
    conversa = Conversa.objects.create(clinica=clinica, paciente=paciente, canal=canal)
    return paciente, canal, conversa


@pytest.mark.django_db(transaction=True)
def test_process_inbound_message_eco_mvp(clinica_a):
    """Fluxo completo do eco MVP: entrada → saída + outbox enfileirado.

    Carrega Mensagem(direcao=entrada) → atualiza Conversa →
    cria Mensagem(direcao=saida, conteudo=ECO_MVP, external_id=NULL)
    → cria Outbox apontando para a mensagem de saída.
    """
    with tenant_session(clinica_a.id):
        _, canal, conversa = _setup_conversa(clinica_a)
        entrada = Mensagem.objects.create(
            conversa=conversa,
            canal=canal,
            direcao=Mensagem.Direcao.ENTRADA,
            remetente="+5511999111111",
            conteudo="oi, gostaria de marcar consulta",
            external_id="wamid_eco_1",
        )

        process_inbound_message(
            clinica_id=clinica_a.id,
            mensagem_id=str(entrada.id),
        )

        # 1. Mensagem de saída com o eco MVP.
        saidas = list(
            Mensagem.objects.filter(
                conversa=conversa,
                direcao=Mensagem.Direcao.SAIDA,
            )
        )
        assert len(saidas) == 1
        saida = saidas[0]
        assert saida.conteudo == ECO_MVP
        assert saida.external_id is None  # Provedor preenche depois.

        # 2. Outbox enfileirado, status pendente, payload referencia a saída.
        outbox = Outbox.objects.filter(clinica=clinica_a).first()
        assert outbox is not None
        assert outbox.status == Outbox.Status.PENDENTE
        assert outbox.tipo == Outbox.Tipo.WHATSAPP_TEXT
        assert outbox.payload["mensagem_id"] == str(saida.id)
        assert outbox.payload["body"] == ECO_MVP
        assert outbox.payload["to_e164"] == "+5511999111111"


@pytest.mark.django_db(transaction=True)
def test_send_outbox_marca_como_enviado(clinica_a):
    """`send_outbox` consome uma linha pendente, chama o stub do
    provider e atualiza para `enviado` com `enviado_em`."""
    with tenant_session(clinica_a.id):
        item = Outbox.objects.create(
            clinica=clinica_a,
            tipo=Outbox.Tipo.WHATSAPP_TEXT,
            payload={"to_e164": "+5511888777666", "body": "olá"},
            proxima_em=timezone.now(),
        )
        assert item.status == Outbox.Status.PENDENTE
        assert item.enviado_em is None

        send_outbox(clinica_id=clinica_a.id, outbox_id=str(item.id))

        item.refresh_from_db()
        assert item.status == Outbox.Status.ENVIADO
        assert item.enviado_em is not None


@pytest.mark.django_db(transaction=True)
def test_send_outbox_idempotente_quando_nao_pendente(clinica_a):
    """Se outra réplica do worker (ou retry) já processou a linha,
    a 2ª invocação retorna None sem alterar nada — defesa contra
    race condition entre workers concorrentes."""
    with tenant_session(clinica_a.id):
        item = Outbox.objects.create(
            clinica=clinica_a,
            tipo=Outbox.Tipo.WHATSAPP_TEXT,
            payload={"to_e164": "+5511777666555", "body": "ping"},
            proxima_em=timezone.now(),
            status=Outbox.Status.ENVIADO,  # Já processado!
            enviado_em=timezone.now(),
        )

        retorno = send_outbox(clinica_id=clinica_a.id, outbox_id=str(item.id))

        assert retorno is None
        item.refresh_from_db()
        # Status permanece ENVIADO; nada foi alterado.
        assert item.status == Outbox.Status.ENVIADO
