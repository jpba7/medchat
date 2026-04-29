"""Modelos do app `clinics`.

`Clinica` é a raiz da tenancy. Não é tenant-owned (não tem `clinica_id`)
— é a tabela que DEFINE os tenants. Toda outra tabela tenant-owned do
sistema faz FK para esta.

`ClinicaCanal` e `ClinicaPolitica` são tenant-owned (uma linha por
clínica) e ficam aqui porque são extensões diretas da configuração da
clínica, não entidades de domínio independentes.
"""

import secrets
import uuid

from django.db import models

from apps.core.models import TenantAwareModel


def _gerar_webhook_secret() -> str:
    """Gera um segredo URL-safe de ~43 chars (32 bytes base64url).

    Usado como `default` do `ClinicaCanal.webhook_secret`. Ser
    callable garante que cada nova linha recebe um valor distinto;
    se fosse `default="..."` literal, todas teriam o mesmo segredo.
    """
    return secrets.token_urlsafe(32)


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


class ClinicaCanal(TenantAwareModel):
    """Canal WhatsApp ligado a uma clínica.

    Cada linha representa um número/instância através do qual a
    clínica recebe mensagens. O webhook do provedor (`Evolution` ou
    `Cloud API`) carrega o `webhook_secret` no header HMAC pra
    autenticar a origem antes de qualquer processamento.

    `config` guarda credenciais/IDs específicos do provedor sem
    schema rígido (os formatos diferem entre Evolution e Cloud) —
    JSONB facilita evoluir sem migration.
    """

    class Tipo(models.TextChoices):
        WHATSAPP_EVOLUTION = "whatsapp_evolution", "WhatsApp via Evolution API"
        WHATSAPP_CLOUD = "whatsapp_cloud", "WhatsApp Cloud API (Meta)"

    tipo = models.CharField(max_length=32, choices=Tipo.choices)
    numero_e164 = models.CharField(
        max_length=16,
        db_index=True,
        help_text="Número no formato E.164, ex.: +5511999999999",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Credenciais/IDs do provedor. Evolution: "
            "{'instance_id': ..., 'token': ...}. Cloud: "
            "{'phone_number_id': ..., 'business_account_id': ...}."
        ),
    )
    webhook_secret = models.CharField(
        max_length=64,
        default=_gerar_webhook_secret,
        help_text=(
            "Segredo HMAC do webhook deste canal. Auto-gerado na "
            "criação. Rotacionar = setar em branco e salvar."
        ),
    )
    ativo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "clinica_canais"
        verbose_name = "canal da clínica"
        verbose_name_plural = "canais da clínica"
        constraints = [
            models.UniqueConstraint(
                fields=["clinica", "tipo"],
                name="canal_unico_por_tipo_por_clinica",
            ),
        ]
        indexes = [
            models.Index(fields=["clinica", "ativo"], name="canal_clinica_ativo_idx"),
        ]

    def save(self, *args, **kwargs):
        # Default callable cobre INSERT, mas se alguém apagou no admin
        # pra rotacionar, regenera aqui antes de salvar.
        if not self.webhook_secret:
            self.webhook_secret = _gerar_webhook_secret()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} • {self.numero_e164}"


class ClinicaPolitica(TenantAwareModel):
    """Política configurável por clínica (chave-valor).

    Em vez de uma coluna por regra, usamos pares chave/valor com
    valor JSONB. Permite adicionar/remover políticas sem migration.
    Exemplos de chaves:

    - `cancelamento_antecedencia_h` → int (horas mínimas)
    - `cpf_obrigatorio` → bool
    - `lembrete_janelas_h` → list[int] (ex.: [24, 2])
    - `saudacao_bot` → str
    - `horario_handoff_humano` → {"inicio": "08:00", "fim": "18:00"}

    `valor` é JSONField pra acomodar tipos heterogêneos por chave.
    A camada de aplicação interpreta cada chave; o banco só guarda.
    """

    chave = models.CharField(max_length=100)
    valor = models.JSONField(
        help_text="Tipo varia por chave (int, str, bool, list, dict).",
    )

    class Meta:
        db_table = "clinica_politicas"
        verbose_name = "política da clínica"
        verbose_name_plural = "políticas da clínica"
        constraints = [
            models.UniqueConstraint(
                fields=["clinica", "chave"],
                name="politica_unica_por_chave_por_clinica",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.chave}={self.valor!r}"
