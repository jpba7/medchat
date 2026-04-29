from django.contrib import admin

from .models import Convenio, Especialidade, Medico


@admin.register(Especialidade)
class EspecialidadeAdmin(admin.ModelAdmin):
    list_display = ("nome", "clinica", "ativo", "criado_em")
    list_filter = ("ativo", "clinica")
    search_fields = ("nome",)
    readonly_fields = ("id", "criado_em", "atualizado_em")


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "crm",
        "especialidade",
        "duracao_consulta_min",
        "ativo",
        "clinica",
    )
    list_filter = ("ativo", "especialidade", "clinica")
    search_fields = ("nome", "crm")
    readonly_fields = ("id", "criado_em", "atualizado_em")


@admin.register(Convenio)
class ConvenioAdmin(admin.ModelAdmin):
    list_display = ("nome", "clinica", "ativo", "criado_em")
    list_filter = ("ativo", "clinica")
    search_fields = ("nome",)
    readonly_fields = ("id", "criado_em", "atualizado_em")
