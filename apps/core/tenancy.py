"""Helpers para abrir sessão Postgres com `app.clinica_id` fora do
ciclo HTTP.

O `RLSMiddleware` cobre views Django, mas Celery tasks rodam fora do
request — precisam declarar o tenant explicitamente. Este módulo
oferece duas formas:

- `tenant_session(clinica_id)` — context manager para uso ad-hoc.
- `@with_tenant` — decorator para Celery tasks; exige `clinica_id`
  como kwarg na chamada.

Ambos usam `transaction.atomic()` + `SET LOCAL`, mantendo o mesmo
contrato do middleware: o setting é descartado ao final da transação,
nunca vaza entre invocações.
"""

from __future__ import annotations

import functools
from contextlib import contextmanager
from typing import Iterator
from uuid import UUID

from django.db import connection, transaction


@contextmanager
def tenant_session(clinica_id: UUID | str) -> Iterator[None]:
    """Abre transação atômica com `app.clinica_id` setado.

    Uso:
        with tenant_session(clinica.id):
            Paciente.objects.create(...)

    Ao sair do bloco (commit ou exception), o `SET LOCAL` expira junto
    com a transação. Se a conexão voltar para o pool, o próximo uso
    parte sem tenant herdado — exatamente o que queremos.
    """
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "SET LOCAL app.clinica_id = %s",
                [str(clinica_id)],
            )
        yield


def with_tenant(func):
    """Decorator que exige `clinica_id` como kwarg da task.

    Lê `kwargs["clinica_id"]`, abre `tenant_session` e executa o corpo
    da task dentro do escopo. Erro explícito se o caller esquecer de
    passar — preferimos crash que vazamento.

    Uso:
        @shared_task
        @with_tenant
        def process_inbound_message(*, clinica_id, mensagem_id):
            # roda dentro de transação com `app.clinica_id` setado
            ...

        process_inbound_message.delay(
            clinica_id=str(clinica.id), mensagem_id=str(msg.id),
        )

    Por que kwarg-only e não posicional: tasks Celery são invocadas via
    `.delay(**kwargs)` ou `.apply_async(kwargs={...})`; forçar kwarg
    elimina ambiguidade de "qual é o primeiro arg" em tasks com
    `bind=True` (que recebem `self`) e em chains/groups.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        clinica_id = kwargs.get("clinica_id")
        if clinica_id is None:
            raise RuntimeError(
                f"{func.__name__}: @with_tenant exige `clinica_id` como "
                "kwarg. Exemplo: tarefa.delay(clinica_id=..., outros=...)."
            )
        with tenant_session(clinica_id):
            return func(*args, **kwargs)

    return wrapper
