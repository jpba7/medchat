from django.contrib import admin

from .models import Clinica, ClinicaCanal, ClinicaPolitica


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


@admin.register(ClinicaCanal)
class ClinicaCanalAdmin(admin.ModelAdmin):
    list_display = ("clinica", "tipo", "numero_e164", "ativo", "criado_em")
    list_filter = ("tipo", "ativo")
    search_fields = ("numero_e164", "clinica__nome", "clinica__slug")
    readonly_fields = ("id", "webhook_secret", "criado_em", "atualizado_em")


@admin.register(ClinicaPolitica)
class ClinicaPoliticaAdmin(admin.ModelAdmin):
    list_display = ("clinica", "chave", "valor", "atualizado_em")
    list_filter = ("chave",)
    search_fields = ("chave", "clinica__nome", "clinica__slug")
    readonly_fields = ("id", "criado_em", "atualizado_em")
