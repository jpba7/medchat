from django.contrib import admin

from .models import EventoBot


@admin.register(EventoBot)
class EventoBotAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "tipo_evento", "conversa", "clinica")
    list_filter = ("tipo_evento", "clinica")
    search_fields = ("dados__icontains",)
    readonly_fields = ("id", "criado_em", "atualizado_em")
    date_hierarchy = "criado_em"
