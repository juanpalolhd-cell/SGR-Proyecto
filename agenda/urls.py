from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_compromisos, name="lista_compromisos"),
    path("nuevo/", views.CompromisoCreateView.as_view(), name="crear_compromiso"),
    path("compromiso/<int:compromiso_id>/", views.detalle_compromiso, name="detalle_compromiso"),
    path("compromiso/<int:compromiso_id>/editar/", views.CompromisoUpdateView.as_view(), name="editar_compromiso"),
    path("compromiso/<int:compromiso_id>/borrar/", views.CompromisoDeleteView.as_view(), name="borrar_compromiso"),
    path("resumen/", views.resumen_agenda, name="resumen_agenda"),
]
