"""Modelos abstract reutilizáveis pelo restante dos apps.

`TenantAwareModel` é a base de toda tabela tenant-owned do MedChat.
Não gera tabela própria (`Meta.abstract = True`); cada modelo concreto
herda e ganha:
    - PK UUID (`id`)
    - FK obrigatório para `clinics.Clinica` (`clinica_id` NOT NULL)
    - timestamps de auditoria (`criado_em`, `atualizado_em`)
    - validação no `save()` que confirma que `self.clinica_id` bate
      com `current_setting('app.clinica_id')` da sessão Postgres
"""

from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import connection, models


class TenantAwareModel(models.Model):
    """Base abstract para tabelas tenant-owned.

    Camada 2 da defesa em profundidade contra vazamento cross-tenant:
    a camada 1 é a policy RLS no Postgres, que filtra leituras e
    escritas baseado em `current_setting('app.clinica_id')`. Esta
    classe valida o mesmo invariante DENTRO da aplicação Django,
    abortando antes do banco se algo escapar (ex.: alguém com role
    `BYPASSRLS` esquece de setar `app.clinica_id` numa task ad-hoc).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    clinica = models.ForeignKey(
        "clinics.Clinica",
        on_delete=models.PROTECT,
        related_name="+",
        db_index=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self._validar_tenant_da_sessao()
        super().save(*args, **kwargs)

    def _validar_tenant_da_sessao(self) -> None:
        """Aborta se `self.clinica_id` não bate com `app.clinica_id`."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.clinica_id', true)")
            row = cursor.fetchone()
        valor_sessao = row[0] if row else None

        if not valor_sessao:
            raise RuntimeError(
                f"{self.__class__.__name__}.save() chamado sem "
                "`app.clinica_id` setado na sessão Postgres. Use o "
                "`RLSMiddleware` (em request HTTP) ou o decorator "
                "`@with_tenant` (em Celery task) antes de salvar."
            )

        if str(self.clinica_id) != valor_sessao:
            raise ValidationError(
                f"{self.__class__.__name__} com clinica_id="
                f"{self.clinica_id} sendo salvo em sessão de "
                f"app.clinica_id={valor_sessao}. Tentativa de "
                "vazamento cross-tenant — abortando."
            )
