"""Modelos do app `catalog` — vocabulário de agendamento.

Esses modelos formam o "menu" que o paciente vê: especialidades
disponíveis, médicos cadastrados, convênios aceitos. Todos
tenant-owned com RLS — clínicas não compartilham nada deste
catálogo.

Through tables (`MedicoConvenio`, `MedicoDisponibilidade`) ficam
no mesmo `models.py` mas são adicionadas em commit/migration
separados.
"""

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TenantAwareModel


class Especialidade(TenantAwareModel):
    """Área de atuação médica. Ex.: Cardiologia, Odontologia, Pediatria.

    Cadastrada manualmente pela clínica via painel. Bot usa pra
    classificar pedido do paciente ("preciso de um cardiologista")
    em uma busca filtrada de médicos.
    """

    nome = models.CharField(max_length=100)
    ativo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "especialidades"
        verbose_name = "especialidade"
        verbose_name_plural = "especialidades"
        constraints = [
            models.UniqueConstraint(
                fields=["clinica", "nome"],
                name="especialidade_unica_por_clinica",
            ),
        ]
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class Medico(TenantAwareModel):
    """Profissional cadastrado por uma clínica.

    `crm` é identificador regulatório (CFM). Unique por clínica
    para evitar duplicata acidental no cadastro. `especialidade`
    é nullable durante onboarding (médico cadastrado antes de
    ter especialidade definida no painel) mas o bot só lista
    médicos com especialidade preenchida.
    """

    nome = models.CharField(max_length=200)
    crm = models.CharField(
        max_length=20,
        help_text="Formato 'NÚMERO/UF', ex.: '123456/SP'.",
    )
    especialidade = models.ForeignKey(
        Especialidade,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Bloqueia deletar especialidade que ainda tem médico.",
    )
    duracao_consulta_min = models.PositiveSmallIntegerField(
        default=30,
        help_text="Duração padrão da consulta em minutos. Usado para gerar slots.",
    )
    ativo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "medicos"
        verbose_name = "médico"
        verbose_name_plural = "médicos"
        constraints = [
            models.UniqueConstraint(
                fields=["clinica", "crm"],
                name="medico_crm_unico_por_clinica",
            ),
        ]
        indexes = [
            models.Index(
                fields=["clinica", "ativo", "especialidade"],
                name="medico_clinica_ativo_esp_idx",
            ),
        ]
        ordering = ["nome"]

    def clean(self) -> None:
        """Bloqueia atribuir especialidade de outra clínica.

        Sem este check, um admin com BYPASSRLS poderia plugar
        `especialidade_id` de uma clínica B em um `Medico` da
        clínica A. RLS na leitura impede o bot de "ver" essa
        FK quebrada, mas a inconsistência fica gravada.
        """
        super().clean()
        if (
            self.especialidade_id is not None
            and self.especialidade.clinica_id != self.clinica_id
        ):
            raise ValidationError(
                {"especialidade": "Especialidade pertence a outra clínica."}
            )

    def __str__(self) -> str:
        return f"{self.nome} ({self.crm})"


class Convenio(TenantAwareModel):
    """Plano de saúde aceito pela clínica. Ex.: Unimed, Bradesco Saúde.

    Cadastro independente de médico — uma clínica pode aceitar
    Unimed mesmo que nenhum médico atenda Unimed ainda. A
    relação concreta (médico X aceita convênio Y) vive em
    `MedicoConvenio`.
    """

    nome = models.CharField(max_length=100)
    ativo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "convenios"
        verbose_name = "convênio"
        verbose_name_plural = "convênios"
        constraints = [
            models.UniqueConstraint(
                fields=["clinica", "nome"],
                name="convenio_unico_por_clinica",
            ),
        ]
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class MedicoConvenio(TenantAwareModel):
    """Vínculo entre médico e convênio com atributos extras.

    Padrão "through table" de Django: Medico×Convenio é M2M, mas
    queremos guardar campos no vínculo (preço, ativo) — então
    declaramos a tabela explicitamente em vez de usar
    `ManyToManyField` puro.

    `clinica_id` é desnormalizado (já vem do FK Medico) por
    decisão de defesa em profundidade: a tabela tem RLS própria,
    então uma query nessa tabela sem `app.clinica_id` setado
    retorna 0 rows (não vaza), em vez de depender do JOIN com
    `medicos` para filtrar via FK.
    """

    medico = models.ForeignKey(
        Medico,
        on_delete=models.CASCADE,
        related_name="+",
    )
    convenio = models.ForeignKey(
        Convenio,
        on_delete=models.CASCADE,
        related_name="+",
    )
    preco_consulta_centavos = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Valor em centavos (sem decimal). Null = usa preço "
            "default da clínica/convênio definido em política."
        ),
    )
    ativo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "medico_convenios"
        verbose_name = "convênio do médico"
        verbose_name_plural = "convênios dos médicos"
        constraints = [
            models.UniqueConstraint(
                fields=["medico", "convenio"],
                name="medico_convenio_unico",
            ),
        ]

    def save(self, *args, **kwargs):
        # Auto-popula clinica_id do FK pai.
        # Se medico e convenio forem de clínicas diferentes, o
        # `clean()` abaixo aborta antes de chegar aqui em fluxos
        # via `full_clean()`; em saves diretos, a validação do
        # TenantAwareModel.save() pega o mismatch contra a sessão.
        if not self.clinica_id and self.medico_id:
            self.clinica_id = self.medico.clinica_id
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        if (
            self.medico_id is not None
            and self.convenio_id is not None
            and self.medico.clinica_id != self.convenio.clinica_id
        ):
            raise ValidationError("Médico e convênio pertencem a clínicas diferentes.")

    def __str__(self) -> str:
        return f"{self.medico} ↔ {self.convenio}"


class MedicoDisponibilidade(TenantAwareModel):
    """Faixa horária semanal recorrente de atendimento de um médico.

    Permite múltiplas faixas/dia (manhã + tarde com almoço entre)
    — não há unique `(medico, dia_semana)`. O cálculo de slots
    livres une todas as faixas de um dia e subtrai os agendamentos
    já marcados.

    `clinica_id` desnormalizado pelo mesmo motivo de
    `MedicoConvenio`: defesa em profundidade.
    """

    class DiaSemana(models.IntegerChoices):
        SEGUNDA = 0, "Segunda"
        TERCA = 1, "Terça"
        QUARTA = 2, "Quarta"
        QUINTA = 3, "Quinta"
        SEXTA = 4, "Sexta"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    medico = models.ForeignKey(
        Medico,
        on_delete=models.CASCADE,
        related_name="+",
    )
    dia_semana = models.PositiveSmallIntegerField(choices=DiaSemana.choices)
    inicio = models.TimeField(help_text="Hora local da clínica (timezone do tenant).")
    fim = models.TimeField()

    class Meta:
        db_table = "medico_disponibilidades"
        verbose_name = "disponibilidade do médico"
        verbose_name_plural = "disponibilidades dos médicos"
        indexes = [
            models.Index(
                fields=["medico", "dia_semana"],
                name="disponibilidade_medico_dia_idx",
            ),
        ]
        ordering = ["medico", "dia_semana", "inicio"]

    def save(self, *args, **kwargs):
        if not self.clinica_id and self.medico_id:
            self.clinica_id = self.medico.clinica_id
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        if self.inicio is not None and self.fim is not None and self.inicio >= self.fim:
            raise ValidationError({"fim": "Hora final deve ser maior que inicial."})

    def __str__(self) -> str:
        return (
            f"{self.medico} • {self.get_dia_semana_display()} {self.inicio}-{self.fim}"
        )
