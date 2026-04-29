"""Modelos do app `appointments`.

`Agendamento` é o ponto onde o produto materializa valor: paciente
escolheu médico+convênio+horário e o bot/atendente registra a
consulta. A invariante mais forte do schema vive aqui — dois
agendamentos ATIVOS do mesmo médico não podem se sobrepor no tempo.
Postgres impõe isso via exclusion constraint, não a aplicação.
"""

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Func, Q

from apps.catalog.models import Convenio, Medico
from apps.core.models import TenantAwareModel
from apps.patients.models import Paciente


class TstzRange(Func):
    """Wrapper Django para a função SQL `tstzrange(start, end)`.

    Necessário porque a exclusion constraint precisa comparar um
    range construído a partir de duas colunas escalares
    (`inicio_em`, `fim_em`) — Postgres não tem range "implícito".
    O `output_field` informa ao ORM que a expressão retorna um
    range timestamptz, então operadores como `&&` (overlap)
    ficam disponíveis.
    """

    function = "tstzrange"
    output_field = DateTimeRangeField()


class Agendamento(TenantAwareModel):
    """Consulta marcada entre paciente e médico.

    Status `cancelado` é tratado como "vaga liberada": a exclusion
    constraint exclui essas linhas do check de overlap, então o
    slot pode ser reutilizado. Outras transições (`realizado`,
    `nao_compareceu`) **continuam ocupando o slot** historicamente
    — não dá pra rebookar uma consulta que já aconteceu.

    `external_event_id`/`external_provider` é prep pra sincronizar
    com calendário do médico (Google/Outlook) na Fase 2+. Hoje fica
    null.
    """

    class Status(models.TextChoices):
        AGENDADO = "agendado", "Agendado"
        REALIZADO = "realizado", "Realizado"
        CANCELADO = "cancelado", "Cancelado"
        NAO_COMPARECEU = "nao_compareceu", "Não compareceu"

    class Origem(models.TextChoices):
        BOT = "bot", "Bot"
        HUMANO = "humano", "Humano"
        IMPORT = "import", "Importação"

    class ExternalProvider(models.TextChoices):
        GOOGLE_CALENDAR = "google_calendar", "Google Calendar"
        OUTLOOK = "outlook", "Outlook"
        APPLE = "apple", "Apple"

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name="+",
    )
    medico = models.ForeignKey(
        Medico,
        on_delete=models.CASCADE,
        related_name="+",
    )
    convenio = models.ForeignKey(
        Convenio,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="PROTECT — não permite deletar convênio que tem agendamento.",
    )
    inicio_em = models.DateTimeField(db_index=True)
    fim_em = models.DateTimeField(
        help_text=(
            "Calculado pelo bot a partir de "
            "`inicio_em + medico.duracao_consulta_min`. Explicito "
            "no schema porque a constraint precisa do range."
        ),
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.AGENDADO,
        db_index=True,
    )
    origem = models.CharField(
        max_length=16,
        choices=Origem.choices,
        default=Origem.BOT,
        help_text="Por onde o agendamento entrou no sistema.",
    )
    external_event_id = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        db_index=True,
        help_text="ID do evento no calendário externo (Google/Outlook).",
    )
    external_provider = models.CharField(
        max_length=32,
        choices=ExternalProvider.choices,
        null=True,
        blank=True,
    )
    cancelado_motivo = models.TextField(
        null=True,
        blank=True,
        help_text="Texto livre do motivo de cancelamento (paciente ou clínica).",
    )

    class Meta:
        db_table = "agendamentos"
        verbose_name = "agendamento"
        verbose_name_plural = "agendamentos"
        constraints = [
            # Tempo invariante: fim depois do início. Evita registros
            # corrompidos antes mesmo da exclusion constraint avaliar.
            models.CheckConstraint(
                condition=Q(inicio_em__lt=F("fim_em")),
                name="agendamento_inicio_antes_de_fim",
            ),
            # Invariante de domínio: dois agendamentos ATIVOS do mesmo
            # médico não podem ocupar tempos sobrepostos. Postgres
            # garante isso a cada INSERT/UPDATE — não há janela de
            # race entre "checa agenda" e "insere".
            #
            # SQL gerado (aproximado):
            #   EXCLUDE USING GIST (
            #     medico_id WITH =,
            #     tstzrange(inicio_em, fim_em) WITH &&
            #   ) WHERE (status != 'cancelado')
            #
            # WHERE exclui canceladas: vaga liberada pode ser reocupada.
            # Status `realizado`/`nao_compareceu` permanecem ativos
            # na constraint — não dá pra rebookar passado.
            ExclusionConstraint(
                name="agendamento_sem_overlap_por_medico",
                expressions=[
                    ("medico", RangeOperators.EQUAL),
                    (TstzRange("inicio_em", "fim_em"), RangeOperators.OVERLAPS),
                ],
                # String literal porque a inner class `Status` ainda
                # não está acessível pelo nome curto dentro de `Meta`
                # (escopo de classe sendo construído).
                condition=~Q(status="cancelado"),
            ),
        ]
        indexes = [
            models.Index(
                fields=["clinica", "inicio_em", "status"],
                name="agend_clinica_data_status_idx",
            ),
            models.Index(
                fields=["paciente", "status"],
                name="agend_paciente_status_idx",
            ),
        ]
        ordering = ["-inicio_em"]

    def clean(self) -> None:
        """Bloqueia FKs cross-tenant (paciente/medico/convenio em outra clínica).

        RLS impede a leitura mas não a escrita se o admin tem
        BYPASSRLS. Este check garante que mesmo via admin Django
        não dá pra plugar paciente da clínica B em agendamento da
        clínica A.
        """
        super().clean()
        problemas = {}
        if self.paciente_id is not None and self.paciente.clinica_id != self.clinica_id:
            problemas["paciente"] = "Paciente pertence a outra clínica."
        if self.medico_id is not None and self.medico.clinica_id != self.clinica_id:
            problemas["medico"] = "Médico pertence a outra clínica."
        if self.convenio_id is not None and self.convenio.clinica_id != self.clinica_id:
            problemas["convenio"] = "Convênio pertence a outra clínica."
        if problemas:
            raise ValidationError(problemas)

    def __str__(self) -> str:
        return f"{self.paciente} ↔ {self.medico} • {self.inicio_em:%d/%m %H:%M}"
