from sgr.legacy import crud
from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_actividades, name="lista_actividades"),
    path("nueva/", crud, {"entidad": "actividades", "accion": "crear"}, name="crear_actividad"),
    path("actividad/<int:actividad_id>/", views.detalle_actividad, name="detalle_actividad"),
    path("actividad/<int:actividad_id>/editar/", crud, {"entidad": "actividades", "accion": "editar"}, name="editar_actividad"),
    path("actividad/<int:actividad_id>/borrar/", crud, {"entidad": "actividades", "accion": "borrar"}, name="borrar_actividad"),
    path("evidencias/", views.lista_evidencias, name="lista_evidencias"),
    path("evidencias/nueva/", crud, {"entidad": "evidencias", "accion": "crear"}, name="crear_evidencia"),
    path("evidencias/<int:evidencia_id>/", views.detalle_evidencia, name="detalle_evidencia"),
    path("evidencias/<int:evidencia_id>/editar/", crud, {"entidad": "evidencias", "accion": "editar"}, name="editar_evidencia"),
    path("evidencias/<int:evidencia_id>/borrar/", crud, {"entidad": "evidencias", "accion": "borrar"}, name="borrar_evidencia"),
]
