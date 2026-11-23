from django.contrib import admin

from .models import Actividad, Evidencia


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ("codigo", "fecha", "persona", "unidad", "item", "estado")
    list_filter = ("estado", "agenda", "unidad")
    search_fields = ("codigo", "descripcion", "item")
    ordering = ("-fecha",)


@admin.register(Evidencia)
class EvidenciaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "actividad", "autor", "fecha", "estado")
    list_filter = ("estado",)
    search_fields = ("codigo", "autor", "observacion")
    ordering = ("-fecha",)

from .models import GestionSocial
admin.site.register(GestionSocial)
