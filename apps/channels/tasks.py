"""Tasks Celery do app `channels`.

`send_outbox` é o consumidor da `Outbox`: pega uma linha
pendente, "envia" via provider e atualiza o status. Na Fase 1
o envio real ainda é stub (apps.channels.providers vem no
item 10). Aqui ficamos com a mecânica de transição
(`pendente → enviado` com `enviado_em`) e o esqueleto para
retry com backoff exponencial.
"""

from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.core.tenancy import with_tenant

from .models import Outbox

# Backoff exponencial em segundos: 30s, 2min, 8min, 32min, 2h.
# Conservador para a Fase 1; ajustar quando virar prod.
_BACKOFF_SEGUNDOS = [30, 120, 480, 1920, 7200]
_MAX_TENTATIVAS = len(_BACKOFF_SEGUNDOS)


def _proxima_tentativa(tentativas: int) -> timezone.datetime:
    """Retorna timestamp do próximo retry baseado em quantas vezes
    a task já tentou. Quando excede `_MAX_TENTATIVAS`, retorna 24h
    no futuro como sentinela (o caller marca como `descartado`)."""
    indice = min(tentativas, _MAX_TENTATIVAS - 1)
    return timezone.now() + timedelta(seconds=_BACKOFF_SEGUNDOS[indice])


@shared_task
@with_tenant
def send_outbox(*, clinica_id, outbox_id):
    """Drena uma linha do Outbox.

    `clinica_id` é obrigatório (kwarg-only) — `@with_tenant`
    abre `tenant_session` e seta `app.clinica_id` antes de o
    corpo rodar. Idempotente: retorna sem fazer nada se a linha
    já não está mais `pendente` (outra réplica do worker pode
    ter pegado primeiro).
    """
    item = Outbox.objects.filter(
        id=outbox_id,
        status=Outbox.Status.PENDENTE,
    ).first()
    if item is None:
        # Já foi processado por outra invocação ou foi cancelado.
        return None

    try:
        # Stub: provider real entra na Fase 1 item 10
        # (apps.channels.providers.evolution / .cloud).
        # Por ora, considera "enviado" automaticamente.
        _entrega_via_provider_stub(item)
    except Exception as exc:  # noqa: BLE001
        item.tentativas += 1
        item.erro_ultimo = repr(exc)
        if item.tentativas >= _MAX_TENTATIVAS:
            item.status = Outbox.Status.DESCARTADO
        else:
            item.status = Outbox.Status.FALHA
            item.proxima_em = _proxima_tentativa(item.tentativas)
        item.save()
        raise

    item.status = Outbox.Status.ENVIADO
    item.enviado_em = timezone.now()
    item.save()
    return str(item.id)


def _entrega_via_provider_stub(item: Outbox) -> None:
    """Stub do envio real. Item 10 substitui pela chamada HTTP.

    Marcado como função separada para que os testes possam
    mockar via `monkeypatch.setattr(send_outbox, "_entrega_...
    via_provider_stub", ...)`.
    """
    # Por ora sucesso silencioso — apenas valida o caminho.
    return None
