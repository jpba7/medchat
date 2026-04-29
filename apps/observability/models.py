"""Modelos do app `observability`.

`EventoBot` é o log local de eventos relevantes do bot — complemento
do Langfuse (que tem o trace de prompt/response detalhado) com um
view operacional acessível direto do Django: o painel da clínica
consegue mostrar "o que aconteceu nessa conversa" sem depender do
Langfuse estar online.
"""

from django.db import models

from apps.core.models import TenantAwareModel
from apps.conversations.models import Conversa


class EventoBot(TenantAwareModel):
    """Evento operacional do bot ligado (geralmente) a uma conversa.

    Pensar como `INFO`/`WARNING`/`ERROR` estruturados, não como log
    de aplicação (use `logging` Python pra isso). Aqui vai apenas
    o que importa para o painel operacional ou auditoria.

    `conversa` é nullable — eventos globais (erro de health check,
    falha de provedor que afeta a clínica toda) não pertencem a
    uma conversa específica. Quando há, `SET_NULL` no delete da
    conversa preserva histórico de eventos para auditoria.

    `dados` JSONB carrega contexto variável por `tipo_evento`:
    - `mensagem_recebida`: `{external_id, conteudo}` (resumo do que chegou)
    - `resposta_enviada`: `{external_id, latencia_ms}`
    - `tool_call`: `{nome, argumentos, resultado}`
    - `erro`: `{stack_trace, exception_type, contexto}`
    - `transicao_status`: `{de, para}`
    """

    class TipoEvento(models.TextChoices):
        MENSAGEM_RECEBIDA = "mensagem_recebida", "Mensagem recebida"
        RESPOSTA_ENVIADA = "resposta_enviada", "Resposta enviada"
        TOOL_CALL = "tool_call", "Chamada de ferramenta"
        ERRO = "erro", "Erro"
        TRANSICAO_STATUS = "transicao_status", "Transição de status"

    conversa = models.ForeignKey(
        Conversa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text=(
            "Null para eventos globais (sem conversa associada). "
            "SET_NULL para preservar evento mesmo se a conversa for "
            "deletada — auditoria não some junto com o dado."
        ),
    )
    tipo_evento = models.CharField(max_length=32, choices=TipoEvento.choices)
    dados = models.JSONField(
        default=dict,
        blank=True,
        help_text="Conteúdo variável por tipo (ver docstring do modelo).",
    )

    class Meta:
        db_table = "eventos_bot"
        verbose_name = "evento do bot"
        verbose_name_plural = "eventos do bot"
        indexes = [
            # Query principal do painel: "últimos eventos de uma clínica".
            models.Index(
                fields=["clinica", "-criado_em"],
                name="evento_clinica_recente_idx",
            ),
            # Query "histórico desta conversa". Parcial pra ignorar
            # eventos sem conversa associada.
            models.Index(
                fields=["conversa", "-criado_em"],
                name="evento_conversa_recente_idx",
                condition=models.Q(conversa__isnull=False),
            ),
        ]
        ordering = ["-criado_em"]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} @ {self.criado_em:%d/%m %H:%M}"
