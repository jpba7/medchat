"""Testes do webhook WhatsApp (`POST /api/webhooks/whatsapp/{canal_id}`).

Cobre o caminho completo do MVP:
- HMAC inválido → 401.
- Canal inexistente ou inativo → 404.
- Payload de mensagem texto → 200, cria Paciente/Conversa/Mensagem
  e dispara `process_inbound_message` (que em modo eager roda
  inline, gerando saída + Outbox).
- Reentrega do provedor (mesmo `external_id`) → 200 + status
  `duplicado` (unique parcial em mensagens fecha a porta).
- Evento não-mensagem (status update, ack) → 200 + `ignorado`,
  sem efeito colateral.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import pytest

from apps.channels.models import Outbox
from apps.clinics.models import ClinicaCanal
from apps.conversations.models import Conversa, Mensagem
from apps.core.tenancy import tenant_session
from apps.patients.models import Paciente


def _hmac_header(secret: str, body: bytes) -> str:
    """Constrói o header `X-Hub-Signature-256` esperado."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _payload_evolution(
    *,
    external_id: str = "wamid_teste_1",
    e164_sem_mais: str = "5511777666555",
    body: str = "Olá, gostaria de marcar consulta",
    push_name: str = "Joana",
) -> dict:
    """Constrói payload mínimo no shape Evolution."""
    return {
        "data": {
            "key": {
                "id": external_id,
                "remoteJid": f"{e164_sem_mais}@s.whatsapp.net",
            },
            "message": {"conversation": body},
            "pushName": push_name,
        }
    }


def _cria_canal(clinica) -> ClinicaCanal:
    """Cria canal Evolution para a clínica. Caller deve estar em
    `tenant_session(clinica.id)`."""
    return ClinicaCanal.objects.create(
        clinica=clinica,
        tipo=ClinicaCanal.Tipo.WHATSAPP_EVOLUTION,
        numero_e164="+5511222333444",
    )


@pytest.mark.django_db(transaction=True)
def test_webhook_canal_nao_encontrado(client):
    """UUID válido mas inexistente → 404."""
    canal_id_falso = uuid.uuid4()
    response = client.post(
        f"/api/webhooks/whatsapp/{canal_id_falso}",
        data="{}",
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256="sha256=qualquer",
    )
    assert response.status_code == 404
    assert response.json() == {"erro": "canal_nao_encontrado"}


@pytest.mark.django_db(transaction=True)
def test_webhook_assinatura_invalida(client, clinica_a):
    """HMAC errado → 401, sem efeito no DB."""
    with tenant_session(clinica_a.id):
        canal = _cria_canal(clinica_a)

    body = json.dumps(_payload_evolution())
    response = client.post(
        f"/api/webhooks/whatsapp/{canal.id}",
        data=body,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256="sha256=errado",
    )
    assert response.status_code == 401
    assert response.json() == {"erro": "assinatura_invalida"}

    # Nenhum efeito colateral — `Mensagem` da clínica permanece vazia.
    with tenant_session(clinica_a.id):
        assert Mensagem.objects.filter(canal=canal).count() == 0


@pytest.mark.django_db(transaction=True)
def test_webhook_aceita_mensagem_e_dispara_eco(client, clinica_a):
    """Caminho feliz — fecha o loop completo do MVP."""
    with tenant_session(clinica_a.id):
        canal = _cria_canal(clinica_a)
    secret = canal.webhook_secret

    payload = _payload_evolution(external_id="wamid_eco_test")
    body = json.dumps(payload).encode("utf-8")

    response = client.post(
        f"/api/webhooks/whatsapp/{canal.id}",
        data=body,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=_hmac_header(secret, body),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "aceito"

    with tenant_session(clinica_a.id):
        # 1. Paciente resolvido a partir do telefone do payload.
        paciente = Paciente.objects.get(telefone_e164="+5511777666555")
        assert paciente.nome == "Joana"

        # 2. Conversa criada no canal certo.
        conversa = Conversa.objects.get(paciente=paciente, canal=canal)
        assert conversa.status == Conversa.Status.BOT

        # 3. Mensagem entrada gravada com external_id.
        entrada = Mensagem.objects.get(
            conversa=conversa, direcao=Mensagem.Direcao.ENTRADA
        )
        assert entrada.external_id == "wamid_eco_test"
        assert entrada.conteudo == "Olá, gostaria de marcar consulta"

        # 4. Eco MVP rodou (eager): mensagem saída + outbox enfileirado.
        saida = Mensagem.objects.get(conversa=conversa, direcao=Mensagem.Direcao.SAIDA)
        assert "Recebi" in saida.conteudo

        outbox = Outbox.objects.filter(clinica=clinica_a).get()
        assert outbox.tipo == Outbox.Tipo.WHATSAPP_TEXT
        assert outbox.payload["mensagem_id"] == str(saida.id)


@pytest.mark.django_db(transaction=True)
def test_webhook_reentrega_e_dedup(client, clinica_a):
    """2ª chamada com mesmo `external_id` → 200 + `duplicado`,
    sem criar Mensagem nova nem disparar eco extra."""
    with tenant_session(clinica_a.id):
        canal = _cria_canal(clinica_a)
    secret = canal.webhook_secret

    payload = _payload_evolution(external_id="wamid_dedup")
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "content_type": "application/json",
        "HTTP_X_HUB_SIGNATURE_256": _hmac_header(secret, body),
    }

    # Primeira entrega — tudo normal.
    r1 = client.post(f"/api/webhooks/whatsapp/{canal.id}", data=body, **headers)
    assert r1.status_code == 200
    assert r1.json()["status"] == "aceito"

    # Reentrega — mesma assinatura, mesmo body. Constraint parcial
    # `(canal, external_id) WHERE external_id IS NOT NULL` rejeita.
    r2 = client.post(f"/api/webhooks/whatsapp/{canal.id}", data=body, **headers)
    assert r2.status_code == 200
    assert r2.json() == {"status": "duplicado"}

    with tenant_session(clinica_a.id):
        # Apenas UMA mensagem entrada apesar das duas requests.
        entradas = Mensagem.objects.filter(
            canal=canal, direcao=Mensagem.Direcao.ENTRADA
        )
        assert entradas.count() == 1


@pytest.mark.django_db(transaction=True)
def test_webhook_evento_sem_mensagem_e_ignorado(client, clinica_a):
    """Status update / ack / mídia (ainda sem suporte) → 200 +
    `ignorado`. Provedor para de retransmitir; nada gravado."""
    with tenant_session(clinica_a.id):
        canal = _cria_canal(clinica_a)
    secret = canal.webhook_secret

    payload = {"event": "messages.update", "data": {"status": "READ"}}
    body = json.dumps(payload).encode("utf-8")

    response = client.post(
        f"/api/webhooks/whatsapp/{canal.id}",
        data=body,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=_hmac_header(secret, body),
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ignorado"}

    with tenant_session(clinica_a.id):
        assert Mensagem.objects.filter(canal=canal).count() == 0
        assert Outbox.objects.filter(clinica=clinica_a).count() == 0
