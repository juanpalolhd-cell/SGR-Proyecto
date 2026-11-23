from django.contrib import admin

from .models import Meta, Periodo


@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "inicio", "termino", "dias_computables", "estado")
    list_filter = ("estado",)
    search_fields = ("nombre",)
    ordering = ("-inicio",)


@admin.register(Meta)
class MetaAdmin(admin.ModelAdmin):
    list_display = ("id", "periodo", "persona", "item", "unidad", "meta", "avance", "ponderador")
    list_filter = ("periodo", "persona", "unidad")
    search_fields = ("item", "persona__nombre")
    ordering = ("periodo", "persona")

from .models import CatalogoMeta
admin.site.register(CatalogoMeta)
