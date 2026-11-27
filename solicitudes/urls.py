from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_solicitudes, name="lista_solicitudes"),
    path("nueva/", views.SolicitudCreateView.as_view(), name="crear_solicitud"),
    path("<int:solicitud_id>/", views.detalle_solicitud, name="detalle_solicitud"),
    path("<int:solicitud_id>/editar/", views.SolicitudUpdateView.as_view(), name="editar_solicitud"),
    path("<int:solicitud_id>/estado/", views.cambiar_estado_solicitud, name="estado_solicitud"),
    path("vecino/<int:vecino_id>/jjvv/", views.vecino_jjvv, name="vecino_jjvv"),
]
