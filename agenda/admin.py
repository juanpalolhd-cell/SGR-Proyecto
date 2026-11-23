from django.contrib import admin

from .models import Compromiso


@admin.register(Compromiso)
class CompromisoAdmin(admin.ModelAdmin):
    list_display = ("id", "territorio", "solicitante", "responsable", "unidad", "estado")
    list_filter = ("estado", "unidad")
    search_fields = ("territorio", "solicitante", "observaciones")
    ordering = ("fecha_comprometida",)

from .models import Hito
admin.site.register(Hito)
