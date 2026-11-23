from sgr.legacy import crud
from django.urls import path

from . import views

urlpatterns = [
    path("unidades/", views.lista_unidades, name="lista_unidades"),
    path("unidades/nueva/", crud, {"entidad": "delegaciones", "accion": "crear"}, name="crear_unidad"),
    path("unidades/<int:unidad_id>/", views.detalle_unidad, name="detalle_unidad"),
    path("unidades/<int:unidad_id>/editar/", crud, {"entidad": "delegaciones", "accion": "editar"}, name="editar_unidad"),
    path("unidades/<int:unidad_id>/borrar/", crud, {"entidad": "delegaciones", "accion": "borrar"}, name="borrar_unidad"),
    path("personas/", views.lista_personas, name="lista_personas"),
    path("personas/nueva/", crud, {"entidad": "funcionarios", "accion": "crear"}, name="crear_persona"),
    path("personas/<int:persona_id>/", views.detalle_persona, name="detalle_persona"),
    path("personas/<int:persona_id>/editar/", crud, {"entidad": "funcionarios", "accion": "editar"}, name="editar_persona"),
    path("personas/<int:persona_id>/borrar/", crud, {"entidad": "funcionarios", "accion": "borrar"}, name="borrar_persona"),
    path("cargos/nuevo/", crud, {"entidad": "cargos", "accion": "crear"}, name="crear_cargo"),
]
