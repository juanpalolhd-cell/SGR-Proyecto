from django.contrib import admin

from .models import (
    Cargo,
    Delegacion,
    Item,
    PerfilUsuario,
    Persona,
    Rol,
    SubAtencion,
    TipoAtencion,
    Unidad,
)


@admin.register(Unidad)
class UnidadAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "responsable", "estado")
    list_filter = ("estado",)
    search_fields = ("nombre", "responsable")
    ordering = ("nombre",)


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "cargo", "delegacion", "estado")
    list_filter = ("estado", "cargo", "delegacion")
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Delegacion)
class DelegacionAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "estado")
    list_filter = ("estado",)
    search_fields = ("codigo", "nombre")
    ordering = ("nombre",)


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "estado")
    list_filter = ("estado",)
    search_fields = ("nombre", "descripcion")
    ordering = ("nombre",)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "rol", "delegacion", "estado")
    list_filter = ("estado", "rol", "delegacion")
    search_fields = ("usuario__username", "rol__nombre")
    ordering = ("usuario__username",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "estado")
    list_filter = ("estado",)
    search_fields = ("codigo", "nombre", "descripcion")
    ordering = ("nombre",)


@admin.register(TipoAtencion)
class TipoAtencionAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "estado")
    list_filter = ("estado",)
    search_fields = ("codigo", "nombre")
    ordering = ("nombre",)


@admin.register(SubAtencion)
class SubAtencionAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo_atencion", "estado")
    list_filter = ("estado", "tipo_atencion")
    search_fields = ("codigo", "nombre", "descripcion")
    ordering = ("tipo_atencion", "nombre")


# Legacy tables retained for restoration/traceability, not a second editable source.
class ArchivoHistoricoAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

for _legacy in (Delegacion, PerfilUsuario, Item):
    if admin.site.is_registered(_legacy): admin.site.unregister(_legacy)
    admin.site.register(_legacy, ArchivoHistoricoAdmin)

from .models import Territorio, Vecino, JuntaVecinos, Participacion
for _model in (Territorio, Vecino, JuntaVecinos, Participacion):
    if not admin.site.is_registered(_model): admin.site.register(_model)
