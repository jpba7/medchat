"""Modelos do app `channels`.

`Outbox` é a fila de envio externo da clínica — toda mensagem
que sai do sistema em direção a um canal (WhatsApp, futuramente
SMS/Email) passa por aqui antes de virar request HTTP. Permite
que `Celery` consuma assíncrono, com retry exponencial e idempotência
do lado do provedor.
"""

from django.db import models

from apps.core.models import TenantAwareModel


class Outbox(TenantAwareModel):
    """Mensagem pendente de envio para canal externo.

    **Outbox pattern** (Hohpe, EIP): em vez de chamar a API do
    provedor direto do request/handler — o que acopla request
    HTTP à API externa — escrevemos uma linha aqui e deixamos
    Celery enviar em background. Vantagens:

    1. Request retorna em ms (não espera HTTP externo).
    2. Crash entre "enviar" e "salvar mensagem" some — se o
       insert na outbox commitou, a task Celery vai pegar
       eventualmente.
    3. Retry com backoff exponencial fica gerenciável (incrementa
       `tentativas`, atualiza `proxima_em`).
    4. Inspeção operacional: query "qual outbox tá travando?"
       no painel.

    `payload` é JSONB livre porque varia por `tipo`:
    - `whatsapp_text`: `{to_e164, body}`
    - `whatsapp_template`: `{to_e164, template_name, params}`
    - `whatsapp_media`: `{to_e164, media_url, caption}`

    Quando o `mensagem_id` da `Mensagem` correspondente já existir
    (caso comum: bot respondeu, gravou Mensagem com external_id
    null, e enfileirou aqui), inclui em `payload.mensagem_id` para
    o consumidor `send_outbox` resolver e atualizar o
    `external_id` após o envio bem-sucedido.
    """

    class Tipo(models.TextChoices):
        WHATSAPP_TEXT = "whatsapp_text", "WhatsApp texto"
        WHATSAPP_TEMPLATE = "whatsapp_template", "WhatsApp template"
        WHATSAPP_MEDIA = "whatsapp_media", "WhatsApp mídia"

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        ENVIADO = "enviado", "Enviado"
        FALHA = "falha", "Falha (com retry)"
        DESCARTADO = "descartado", "Descartado (sem retry)"

    tipo = models.CharField(max_length=24, choices=Tipo.choices)
    payload = models.JSONField(
        help_text=(
            "Dados específicos do tipo: destino, corpo, template, "
            "media URL etc. Inclui `mensagem_id` quando há "
            "linha em `mensagens` para atualizar com o `external_id` "
            "retornado pelo provedor."
        ),
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDENTE,
        db_index=True,
    )
    tentativas = models.PositiveIntegerField(
        default=0,
        help_text="Quantas vezes a task tentou enviar.",
    )
    proxima_em = models.DateTimeField(
        db_index=True,
        help_text=(
            "Quando a task pode tentar enviar de novo. Backoff "
            "exponencial sobe esse valor a cada falha."
        ),
    )
    enviado_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp do envio bem-sucedido.",
    )
    erro_ultimo = models.TextField(
        null=True,
        blank=True,
        help_text="Mensagem do último erro do provedor.",
    )

    class Meta:
        db_table = "outbox"
        verbose_name = "item da outbox"
        verbose_name_plural = "outbox"
        indexes = [
            # Query principal do consumidor `send_outbox`:
            # "quais itens pendentes estão prontos para enviar?"
            # Index parcial em status='pendente' deixaria o índice
            # ainda menor, mas o choices é suficiente como filtro
            # — manter simples na Fase 1.
            models.Index(
                fields=["clinica", "status", "proxima_em"],
                name="outbox_clinica_pronto_idx",
            ),
        ]
        ordering = ["proxima_em"]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} • {self.get_status_display()} (tentativas={self.tentativas})"
