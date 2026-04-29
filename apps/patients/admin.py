from django.contrib import admin

from .models import Paciente


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "telefone_e164", "clinica", "lgpd_aceito_em", "criado_em")
    list_filter = ("clinica",)
    search_fields = ("nome", "telefone_e164", "cpf")
    readonly_fields = ("id", "criado_em", "atualizado_em")
