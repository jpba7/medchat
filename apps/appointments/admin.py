from django.contrib import admin

from .models import Agendamento


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = (
        "paciente",
        "medico",
        "inicio_em",
        "status",
        "origem",
        "clinica",
    )
    list_filter = ("status", "origem", "clinica")
    search_fields = (
        "paciente__nome",
        "paciente__telefone_e164",
        "medico__nome",
        "external_event_id",
    )
    readonly_fields = ("id", "criado_em", "atualizado_em")
    date_hierarchy = "inicio_em"
