"""NinjaAPI raiz do MedChat.

Endpoints aqui:

- `/ready` e `/health` — health checks (públicos, não exigem tenant).
- `/webhooks/whatsapp/{canal_id}` — entrypoint do webhook
  WhatsApp. Resolve o tenant pelo `canal_id` (path) em vez de
  header, então também é público em nível de middleware (`/api/
  webhooks/` está em `PUBLIC_PATH_PREFIXES`); o handler abre
  `tenant_session` manualmente após validar HMAC.

Endpoints de domínio (paciente, agendamento, conversa) virão em
routers separados e usarão o caminho normal via `X-Clinic-Slug` +
`RLSMiddleware`.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from django.core.cache import cache
from django.db import IntegrityError, connection, transaction
from django.http import HttpRequest, JsonResponse
from ninja import NinjaAPI

from apps.channels.webhook import parse_evolution_payload, verifica_hmac_sha256

logger = logging.getLogger(__name__)

api = NinjaAPI(
    title="MedChat API",
    version="1.0.0",
    description="Backend do MedChat — secretária virtual de clínicas via WhatsApp.",
)


def _check_postgres() -> str:
    """Confirma que o banco aceita queries simples. Retorna 'ok' ou
    string com prefixo `erro:` para diagnóstico no payload."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # noqa: BLE001 — health check captura qualquer falha
        return f"erro: {exc!r}"
    return "ok"


def _check_redis() -> str:
    """Round-trip set/get no cache (Redis configurado em `base.py`)."""
    try:
        cache.set("health-check", "1", timeout=5)
        if cache.get("health-check") != "1":
            return "round_trip_falhou"
    except Exception as exc:  # noqa: BLE001
        return f"erro: {exc!r}"
    return "ok"


def _check_celery() -> str:
    """Pinga workers via Celery broadcast. `no_workers` quando o
    broker está OK mas nenhum worker respondeu no timeout — distinto
    de `erro` (broker indisponível)."""
    try:
        # Import local para deixar o módulo importável mesmo se Celery
        # estiver com algum problema de inicialização (não bloqueia
        # `/ready`, que não chama esta função).
        from config.celery import app as celery_app

        respostas = celery_app.control.ping(timeout=2)
        if not respostas:
            return "no_workers"
    except Exception as exc:  # noqa: BLE001
        return f"erro: {exc!r}"
    return "ok"


def _resposta_health(checks: dict[str, str]) -> JsonResponse:
    """Constrói a resposta com `status` agregado e código HTTP coerente."""
    saudavel = all(valor == "ok" for valor in checks.values())
    payload: dict[str, Any] = {
        "status": "ok" if saudavel else "degraded",
        "checks": checks,
    }
    return JsonResponse(payload, status=200 if saudavel else 503)


@api.get("/ready", summary="Readiness probe", tags=["health"])
def ready(request: HttpRequest) -> JsonResponse:
    """Postgres responde a `SELECT 1` → pronto pra tráfego."""
    checks = {"postgres": _check_postgres()}
    return _resposta_health(checks)


@api.get("/health", summary="Liveness probe + dependências", tags=["health"])
def health(request: HttpRequest) -> JsonResponse:
    """Postgres + Redis + Celery (workers respondendo a ping)."""
    checks = {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
        "celery": _check_celery(),
    }
    return _resposta_health(checks)


@api.post(
    "/webhooks/whatsapp/{canal_id}",
    summary="Webhook entrante WhatsApp (Evolution / Cloud)",
    tags=["webhooks"],
)
def webhook_whatsapp(request: HttpRequest, canal_id: UUID) -> JsonResponse:
    """Entrypoint do webhook WhatsApp para um canal específico.

    Fluxo:
    1. Resolve `ClinicaCanal` por `canal_id` (path). 404 se não
       existe ou está inativo.
    2. Valida HMAC-SHA256 do body com `webhook_secret` do canal.
       401 em assinatura inválida ou ausente.
    3. Parse mínimo do payload (Evolution shape). Eventos não-
       mensagem (status update, ack) → 200 + `status: ignorado`,
       sem fluxo.
    4. Abre `tenant_session(canal.clinica_id)` (path é público no
       middleware, então RLS não foi setada antes).
    5. Resolve/cria `Paciente` por `(clinica, telefone_e164)` e
       `Conversa` ativa por `(clinica, paciente, canal)`.
    6. Insere `Mensagem` (entrada) — unique parcial `(canal,
       external_id) WHERE external_id IS NOT NULL` dispara
       `IntegrityError` em reentrega → 200 + `status: duplicado`.
    7. Despacha `process_inbound_message.delay(task_id=external_id,
       ...)` — `task_id` dá idempotência adicional via Celery
       (broker descarta retry com mesmo id).

    Imports locais para evitar carga ao importar `config.api`
    (necessário pra que o NinjaAPI seja construído rapidamente
    durante checks Django).
    """
    from apps.clinics.models import ClinicaCanal
    from apps.conversations.models import Conversa, Mensagem
    from apps.conversations.tasks import process_inbound_message
    from apps.core.tenancy import tenant_session
    from apps.patients.models import Paciente

    canal = ClinicaCanal.objects.filter(id=canal_id, ativo=True).first()
    if canal is None:
        return JsonResponse({"erro": "canal_nao_encontrado"}, status=404)

    raw_body = request.body
    assinatura = request.headers.get("X-Hub-Signature-256", "")
    if not verifica_hmac_sha256(raw_body, assinatura, canal.webhook_secret):
        logger.warning(
            "webhook_assinatura_invalida",
            extra={"canal_id": str(canal_id)},
        )
        return JsonResponse({"erro": "assinatura_invalida"}, status=401)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return JsonResponse({"erro": "json_invalido"}, status=400)

    parsed = parse_evolution_payload(payload)
    if parsed is None:
        # Evento sem mensagem de texto (status update, ack, mídia).
        # 200 obrigatório — provedor para de retransmitir.
        return JsonResponse({"status": "ignorado"}, status=200)

    with tenant_session(canal.clinica_id):
        paciente, _ = Paciente.objects.get_or_create(
            clinica=canal.clinica,
            telefone_e164=parsed["from_e164"],
            defaults={"nome": parsed["push_name"] or parsed["from_e164"]},
        )

        # Conversa ativa = aquela que ainda não foi encerrada.
        # Filtro com `.exclude(status=ENCERRADA)` permite reabrir
        # diálogo sem reusar uma conversa já fechada.
        conversa = (
            Conversa.objects.filter(
                clinica=canal.clinica, paciente=paciente, canal=canal
            )
            .exclude(status=Conversa.Status.ENCERRADA)
            .first()
        )
        if conversa is None:
            conversa = Conversa.objects.create(
                clinica=canal.clinica, paciente=paciente, canal=canal
            )

        # Savepoint dedicado para capturar IntegrityError sem
        # quebrar a transação outer (`tenant_session`).
        try:
            with transaction.atomic():
                mensagem = Mensagem.objects.create(
                    conversa=conversa,
                    canal=canal,
                    direcao=Mensagem.Direcao.ENTRADA,
                    remetente=parsed["from_e164"],
                    conteudo=parsed["body"],
                    external_id=parsed["external_id"],
                    payload_raw=payload,
                )
        except IntegrityError:
            logger.info(
                "webhook_mensagem_duplicada",
                extra={
                    "canal_id": str(canal_id),
                    "external_id": parsed["external_id"],
                },
            )
            return JsonResponse({"status": "duplicado"}, status=200)

        process_inbound_message.apply_async(
            kwargs={
                "clinica_id": str(canal.clinica_id),
                "mensagem_id": str(mensagem.id),
            },
            # `task_id=external_id` dá idempotência via Celery —
            # se o broker já tiver recebido essa task, descarta a
            # 2ª. Defesa em profundidade junto com a unique parcial.
            task_id=parsed["external_id"],
        )

    return JsonResponse(
        {"status": "aceito", "mensagem_id": str(mensagem.id)},
        status=200,
    )
