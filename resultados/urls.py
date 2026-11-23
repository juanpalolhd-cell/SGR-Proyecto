from sgr.legacy import crud
from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_metas, name="lista_metas"),
    path("meta/nueva/", crud, {"entidad": "asignaciones", "accion": "crear"}, name="crear_meta"),
    path("meta/<int:meta_id>/", views.detalle_meta, name="detalle_meta"),
    path("meta/<int:meta_id>/editar/", crud, {"entidad": "asignaciones", "accion": "editar"}, name="editar_meta"),
    path("meta/<int:meta_id>/borrar/", crud, {"entidad": "asignaciones", "accion": "borrar"}, name="borrar_meta"),
    path("periodo/nuevo/", crud, {"entidad": "trimestres", "accion": "crear"}, name="crear_periodo"),
    path("persona/<int:persona_id>/", views.resultado_persona, name="resultado_persona"),
    path("tablero/", views.tablero_unidad, name="tablero_unidad"),
    path("informe/", views.informe_resumen, name="informe_resumen"),
]
