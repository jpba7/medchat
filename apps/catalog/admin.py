from django.contrib import admin

from .models import (
    Convenio,
    Especialidade,
    Medico,
    MedicoConvenio,
    MedicoDisponibilidade,
)


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


@admin.register(MedicoConvenio)
class MedicoConvenioAdmin(admin.ModelAdmin):
    list_display = ("medico", "convenio", "preco_consulta_centavos", "ativo")
    list_filter = ("ativo", "convenio")
    search_fields = ("medico__nome", "convenio__nome")
    readonly_fields = ("id", "clinica", "criado_em", "atualizado_em")


@admin.register(MedicoDisponibilidade)
class MedicoDisponibilidadeAdmin(admin.ModelAdmin):
    list_display = ("medico", "dia_semana", "inicio", "fim")
    list_filter = ("dia_semana", "medico__clinica")
    search_fields = ("medico__nome",)
    readonly_fields = ("id", "clinica", "criado_em", "atualizado_em")
