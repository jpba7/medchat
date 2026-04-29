from django.contrib import admin

from .models import Outbox


@admin.register(Outbox)
class OutboxAdmin(admin.ModelAdmin):
    list_display = (
        "tipo",
        "status",
        "tentativas",
        "proxima_em",
        "enviado_em",
        "clinica",
    )
    list_filter = ("status", "tipo", "clinica")
    search_fields = ("payload__icontains", "erro_ultimo")
    readonly_fields = ("id", "criado_em", "atualizado_em")
    date_hierarchy = "criado_em"
