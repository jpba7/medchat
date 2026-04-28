"""Middleware que resolve o tenant da request e seta `app.clinica_id`.

Como funciona:
1. Endpoints na whitelist (`/api/health`, `/api/ready`, `/admin/`)
   passam direto, sem tenant.
2. Demais endpoints precisam declarar o tenant. Resolução em ordem:
    a. Header `X-Clinic-Slug` — usado pelo painel administrativo.
    b. (TODO) Path `/api/webhooks/whatsapp/<canal_id>/` — quando o
       app `channels` tiver o modelo `ClinicaCanal`, lookup pelo
       canal_id resolve para a clínica.
3. Se o tenant é resolvido, abre `transaction.atomic()` e executa
   `SET LOCAL app.clinica_id = '<uuid>'` antes de chamar a view.
4. Se o tenant não pode ser resolvido em endpoint privado, retorna
   500 com log estruturado — fail-loud, nunca silencia. Lista vazia
   por RLS sem tenant é o pior tipo de bug em multi-tenant.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from django.db import connection, transaction
from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger(__name__)


PUBLIC_PATH_PREFIXES: tuple[str, ...] = (
    "/api/health",
    "/api/ready",
    "/admin",
    "/static",
)


class RLSMiddleware:
    """Resolve `clinica_id` e injeta na sessão Postgres da request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self._is_public(request):
            return self.get_response(request)

        clinica_id = self._resolve_tenant(request)
        if clinica_id is None:
            logger.warning(
                "rls_tenant_nao_resolvido",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "tem_header_slug": "X-Clinic-Slug" in request.headers,
                },
            )
            return JsonResponse(
                {"erro": "tenant_nao_resolvido"},
                status=500,
            )

        # `SET LOCAL` é válido apenas até o COMMIT/ROLLBACK da transação
        # atual; envolvemos a execução da view em `atomic()` para que o
        # escopo cubra todas as queries da view e seja descartado ao
        # final, evitando vazamento entre requests reusando conexão.
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL app.clinica_id = %s",
                    [str(clinica_id)],
                )
            return self.get_response(request)

    @staticmethod
    def _is_public(request: HttpRequest) -> bool:
        return any(
            request.path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES
        )

    @staticmethod
    def _resolve_tenant(request: HttpRequest) -> Optional[UUID]:
        """Resolve a clínica do request. Retorna `None` se não encontrar."""
        slug = request.headers.get("X-Clinic-Slug")
        if slug:
            # Late import: evita cycle (clinics importa de core indiretamente
            # quando seus modelos herdarem TenantAwareModel no futuro).
            from apps.clinics.models import Clinica

            clinica_id = (
                Clinica.objects.filter(slug=slug, ativa=True)
                .values_list("id", flat=True)
                .first()
            )
            return clinica_id

        # TODO(channels): resolver por canal_id quando webhook estiver
        # no ar. Padrão: /api/webhooks/whatsapp/<canal_uuid>/ →
        # ClinicaCanal.objects.get(id=canal_uuid).clinica_id.
        return None
