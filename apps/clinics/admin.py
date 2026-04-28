from django.contrib import admin

from .models import Clinica


@admin.register(Clinica)
class ClinicaAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "cnpj", "ativa", "criado_em")
    list_filter = ("ativa",)
    search_fields = ("nome", "slug", "cnpj")
    readonly_fields = ("id", "criado_em", "atualizado_em")
    prepopulated_fields = {"slug": ("nome",)}
    fieldsets = (
        (None, {"fields": ("nome", "slug", "ativa")}),
        ("Identificação fiscal", {"fields": ("cnpj",)}),
        ("Configuração operacional", {"fields": ("timezone", "horario_comercial")}),
        ("Auditoria", {"fields": ("id", "criado_em", "atualizado_em")}),
    )
