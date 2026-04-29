"""Modelos do app `patients`.

`Paciente` é a entidade central do bot — todo fluxo (agendar,
cancelar, enviar lembrete, escalar handoff) começa resolvendo
"quem é o paciente?" a partir do número WhatsApp.
"""

from django.db import models

from apps.core.models import TenantAwareModel


class Paciente(TenantAwareModel):
    """Paciente de uma clínica. Identificado pelo telefone E.164.

    Criado automaticamente pelo handler do webhook quando uma
    mensagem chega de um número desconhecido. CPF é opcional —
    cada clínica decide via política `cpf_obrigatorio`. LGPD é
    rastreado em `lgpd_aceito_em`: enquanto `null`, o bot mostra
    aviso de privacidade no primeiro contato.
    """

    telefone_e164 = models.CharField(
        max_length=16,
        db_index=True,
        help_text="Formato E.164 com '+' e código país, ex.: +5511999999999.",
    )
    nome = models.CharField(
        max_length=200,
        help_text=(
            "Resolvido do `pushName` do WhatsApp na primeira mensagem. "
            "Bot pode pedir confirmação/correção depois."
        ),
    )
    cpf = models.CharField(
        max_length=14,
        null=True,
        default=None,
        blank=True,
        help_text=(
            "Apenas dígitos, sem máscara. Opcional por padrão — "
            "torna-se obrigatório se a política `cpf_obrigatorio` "
            "da clínica for True."
        ),
    )
    lgpd_aceito_em = models.DateTimeField(
        null=True,
        default=None,
        blank=True,
        help_text=(
            "Timestamp do aceite do aviso LGPD. Enquanto null, o "
            "bot apresenta o texto da política `lgpd_texto` antes "
            "de qualquer outra interação."
        ),
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Dados auxiliares: `pushName` original do WhatsApp, "
            "tags de segmentação, anotações livres."
        ),
    )

    class Meta:
        db_table = "pacientes"
        verbose_name = "paciente"
        verbose_name_plural = "pacientes"
        constraints = [
            models.UniqueConstraint(
                fields=["clinica", "telefone_e164"],
                name="paciente_unico_por_telefone_por_clinica",
            ),
        ]
        indexes = [
            # Index parcial: só pacientes que preencheram CPF.
            # Reduz tamanho do index quando a maioria não tem CPF.
            models.Index(
                fields=["cpf"],
                name="paciente_cpf_idx",
                condition=models.Q(cpf__isnull=False),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nome} ({self.telefone_e164})"
