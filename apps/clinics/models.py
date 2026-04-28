"""Modelos do app `clinics`.

`Clinica` é a raiz da tenancy. Não é tenant-owned (não tem `clinica_id`)
— é a tabela que DEFINE os tenants. Toda outra tabela tenant-owned do
sistema faz FK para esta.
"""

import uuid

from django.db import models


class Clinica(models.Model):
    """Cliente B2B do MedChat. Cada linha é um tenant.

    Esta tabela é GLOBAL — sem RLS, sem `clinica_id`. Acesso direto a
    `Clinica` é feito antes do `RLSMiddleware` resolver o tenant
    corrente (o middleware precisa ler aqui pra saber quem é o tenant
    e setar `app.clinica_id` na sessão).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    nome = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=80,
        unique=True,
        db_index=True,
        help_text=(
            "Identificador URL-safe da clínica. Usado no header "
            "`X-Clinic-Slug` para resolver o tenant em requests do painel."
        ),
    )
    cnpj = models.CharField(
        max_length=14,
        blank=True,
        help_text="Apenas dígitos. Sem máscara.",
    )
    timezone = models.CharField(
        max_length=64,
        default="America/Sao_Paulo",
        help_text="Timezone IANA. Lembretes e horário comercial respeitam este valor.",
    )
    horario_comercial = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Janelas de atendimento humano por dia da semana. Formato: "
            "{'seg': [['08:00', '18:00']], 'sab': [['08:00', '12:00']], ...}. "
            "Fora dessas janelas, o bot responde sozinho mas não escala handoff."
        ),
    )
    ativa = models.BooleanField(
        default=True,
        help_text=(
            "Quando False, webhooks são aceitos mas não disparam tasks. "
            "Soft-disable para clientes em débito ou em onboarding."
        ),
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clinicas"
        verbose_name = "clínica"
        verbose_name_plural = "clínicas"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome
