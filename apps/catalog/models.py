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
