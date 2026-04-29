from django.contrib import admin

from .models import Conversa, Handoff, Mensagem


@admin.register(Conversa)
class ConversaAdmin(admin.ModelAdmin):
    list_display = ("paciente", "canal", "status", "criado_em", "encerrado_em")
    list_filter = ("status", "canal")
    search_fields = ("paciente__nome", "paciente__telefone_e164")
    readonly_fields = ("id", "criado_em", "atualizado_em")


@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "conversa", "direcao", "remetente", "external_id")
    list_filter = ("direcao", "canal")
    search_fields = ("remetente", "conteudo", "external_id")
    readonly_fields = ("id", "clinica", "criado_em", "atualizado_em")
    date_hierarchy = "criado_em"


@admin.register(Handoff)
class HandoffAdmin(admin.ModelAdmin):
    list_display = ("conversa", "gatilho", "aceito_por", "criado_em", "encerrado_em")
    list_filter = ("gatilho", "clinica")
    search_fields = ("aceito_por", "resolucao")
    readonly_fields = ("id", "clinica", "criado_em", "atualizado_em")
