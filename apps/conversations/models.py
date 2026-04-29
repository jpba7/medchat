"""Modelos do app `conversations`.

Onde a conversa entre paciente e bot/atendente vira dado
estruturado. Três tabelas:

- `Conversa` — o "fio" — agrupa todas as mensagens trocadas
  com um paciente em um canal específico. Tem máquina de
  estados (`bot` ↔ `handoff_*` ↔ `encerrada`).
- `Mensagem` — cada turn da conversa (entrada do paciente ou
  saída do bot/atendente). Unique parcial `(canal, external_id)`
  garante idempotência: webhook que reentrega não duplica.
- `Handoff` — registro de cada vez que o bot pediu/recebeu
  ajuda humana. Múltiplos por conversa (atendente sai → bot
  retorna → outro handoff abre).
"""

from django.core.exceptions import ValidationError
from django.db import models

from apps.clinics.models import ClinicaCanal
from apps.core.models import TenantAwareModel
from apps.patients.models import Paciente


class Conversa(TenantAwareModel):
    """Conversa em curso entre paciente e canal da clínica.

    Status implementa máquina de estados informal:

    - `bot` — bot está respondendo. Estado normal.
    - `handoff_aguardando` — bot escalou; nenhum atendente aceitou ainda.
    - `handoff_ativo` — atendente humano está conduzindo.
    - `encerrada` — terminada (resolveu, paciente sumiu, bot encerrou).

    `contexto` JSONB guarda estado transitório do fluxo bot —
    intenção detectada, slot fillers ("que dia?", "qual médico?"),
    flags. Não é histórico de mensagens — isso vai em `Mensagem`.
    """

    class Status(models.TextChoices):
        BOT = "bot", "Bot ativo"
        HANDOFF_AGUARDANDO = "handoff_aguardando", "Aguardando atendente"
        HANDOFF_ATIVO = "handoff_ativo", "Atendente conduzindo"
        ENCERRADA = "encerrada", "Encerrada"

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name="+",
    )
    canal = models.ForeignKey(
        ClinicaCanal,
        on_delete=models.CASCADE,
        related_name="+",
        help_text="Canal pelo qual a conversa está acontecendo.",
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.BOT,
        db_index=True,
    )
    contexto = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Estado transitório do fluxo bot: intenção detectada, "
            "slot fillers, flags. Não é histórico de mensagens."
        ),
    )
    encerrado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "conversas"
        verbose_name = "conversa"
        verbose_name_plural = "conversas"
        indexes = [
            # Inbox por status (humano olhando "quem precisa de mim").
            models.Index(
                fields=["clinica", "status"],
                name="conv_clinica_status_idx",
            ),
            # Histórico do paciente — últimas conversas primeiro.
            models.Index(
                fields=["paciente", "-criado_em"],
                name="conv_paciente_recente_idx",
            ),
        ]
        ordering = ["-criado_em"]

    def clean(self) -> None:
        super().clean()
        problemas = {}
        if self.paciente_id is not None and self.paciente.clinica_id != self.clinica_id:
            problemas["paciente"] = "Paciente pertence a outra clínica."
        if self.canal_id is not None and self.canal.clinica_id != self.clinica_id:
            problemas["canal"] = "Canal pertence a outra clínica."
        if problemas:
            raise ValidationError(problemas)

    def __str__(self) -> str:
        return f"{self.paciente} via {self.canal} [{self.get_status_display()}]"


class Mensagem(TenantAwareModel):
    """Turn de uma conversa — entrada (paciente) ou saída (bot/atendente).

    `external_id` é o ID que o provedor (Evolution / WhatsApp Cloud)
    atribui à mensagem. Mensagens GERADAS localmente pelo bot/atendente
    deixam `external_id` nulo até o `send_outbox` confirmar entrega
    e gravar o ID retornado pelo provedor.

    A unique parcial `(canal, external_id) WHERE external_id IS NOT
    NULL` é o pilar de idempotência do webhook — Postgres rejeita
    qualquer reentrega como conflito antes de chegar no Celery.

    `clinica_id` é desnormalizado (auto-populado do FK conversa)
    para que a tabela tenha RLS própria, sem depender de JOIN com
    `conversas` para filtrar por tenant.
    """

    class Direcao(models.TextChoices):
        ENTRADA = "entrada", "Recebida (paciente → sistema)"
        SAIDA = "saida", "Enviada (sistema → paciente)"

    conversa = models.ForeignKey(
        Conversa,
        on_delete=models.CASCADE,
        related_name="+",
    )
    canal = models.ForeignKey(
        ClinicaCanal,
        on_delete=models.CASCADE,
        related_name="+",
        help_text=(
            "Redundante (mesmo canal da conversa) — preenchido para "
            "queries de idempotência sem JOIN."
        ),
    )
    direcao = models.CharField(max_length=8, choices=Direcao.choices)
    remetente = models.CharField(
        max_length=256,
        help_text=(
            "Identificador de quem enviou: E.164 do paciente em "
            "entradas; nome do bot ou ID do atendente em saídas."
        ),
    )
    conteudo = models.TextField(help_text="Texto da mensagem.")
    payload_raw = models.JSONField(
        default=dict,
        blank=True,
        help_text="Payload bruto do provedor (Evolution/Cloud) para debug.",
    )
    external_id = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "ID atribuído pelo provedor. Null em mensagens geradas "
            "localmente que ainda não foram enviadas."
        ),
    )

    class Meta:
        db_table = "mensagens"
        verbose_name = "mensagem"
        verbose_name_plural = "mensagens"
        constraints = [
            # Idempotência de webhook: o provedor pode reenviar a
            # mesma mensagem (timeout, retry, At-Least-Once). A
            # constraint parcial garante que só conta UMA por
            # `(canal, external_id)`. Mensagens locais (saídas
            # ainda não confirmadas pelo provedor) têm
            # `external_id NULL` e ficam fora da constraint —
            # podem coexistir em qualquer quantidade.
            models.UniqueConstraint(
                fields=["canal", "external_id"],
                condition=models.Q(external_id__isnull=False),
                name="msg_canal_external_id_unico_se_presente",
            ),
        ]
        indexes = [
            models.Index(
                fields=["conversa", "criado_em"],
                name="msg_conversa_data_idx",
            ),
        ]
        ordering = ["criado_em"]

    def save(self, *args, **kwargs):
        # Auto-popula clinica_id da conversa (mesmo padrão das
        # through-tables do catalog) antes de o save() do
        # TenantAwareModel validar contra a sessão.
        if not self.clinica_id and self.conversa_id:
            self.clinica_id = self.conversa.clinica_id
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        problemas = {}
        if self.conversa_id is not None and self.conversa.clinica_id != self.clinica_id:
            problemas["conversa"] = "Conversa pertence a outra clínica."
        if (
            self.canal_id is not None
            and self.conversa_id is not None
            and self.canal_id != self.conversa.canal_id
        ):
            problemas["canal"] = "Canal da mensagem ≠ canal da conversa."
        if problemas:
            raise ValidationError(problemas)

    def __str__(self) -> str:
        prefixo = "→" if self.direcao == self.Direcao.ENTRADA else "←"
        return f"{prefixo} {self.remetente}: {self.conteudo[:60]}"


class Handoff(TenantAwareModel):
    """Registro de cada vez que a conversa precisou de humano.

    Múltiplos handoffs por conversa são esperados: atendente
    resolve algo → bot retoma → bot trava de novo → outro
    handoff. `encerrado_em` IS NULL marca o handoff atual.

    `clinica_id` desnormalizado (auto-populado da conversa) pelo
    mesmo motivo que `Mensagem`.
    """

    class Gatilho(models.TextChoices):
        PEDIDO_EXPLICITO = "pedido_explicito", "Paciente pediu humano"
        CONFIANCA_BAIXA = "confianca_baixa", "Bot incerto"
        URGENCIA_MEDICA = "urgencia_medica", "Sinal de urgência"
        RECLAMACAO = "reclamacao", "Reclamação detectada"

    conversa = models.ForeignKey(
        Conversa,
        on_delete=models.CASCADE,
        related_name="+",
    )
    gatilho = models.CharField(max_length=24, choices=Gatilho.choices)
    aceito_por = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        help_text="Identificador do atendente que assumiu (livre por enquanto).",
    )
    encerrado_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Null = handoff em aberto.",
    )
    resolucao = models.TextField(
        null=True,
        blank=True,
        help_text="Resumo livre de como o atendimento foi resolvido.",
    )

    class Meta:
        db_table = "handoffs"
        verbose_name = "handoff"
        verbose_name_plural = "handoffs"
        indexes = [
            # Inbox humano por clínica — abertos primeiro (criado_em DESC).
            models.Index(
                fields=["clinica", "-criado_em"],
                name="handoff_clinica_recente_idx",
            ),
            models.Index(fields=["conversa"], name="handoff_conversa_idx"),
        ]
        ordering = ["-criado_em"]

    def save(self, *args, **kwargs):
        if not self.clinica_id and self.conversa_id:
            self.clinica_id = self.conversa.clinica_id
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        if self.conversa_id is not None and self.conversa.clinica_id != self.clinica_id:
            raise ValidationError({"conversa": "Conversa pertence a outra clínica."})

    def __str__(self) -> str:
        estado = "aberto" if self.encerrado_em is None else "fechado"
        return f"Handoff [{self.get_gatilho_display()}] {estado}"
