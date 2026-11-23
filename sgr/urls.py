from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from sgr.auth_views import LoginView, LogoutView
from sgr.search_views import BusquedaGlobalView
from sgr import catalog_views as cv

urlpatterns = [
    path('gestion/', cv.index, name='catalog_index'),
    path('gestion/<slug:entidad>/', cv.Listado.as_view(), name='catalog_lista'),
    path('gestion/<slug:entidad>/crear/', cv.Crear.as_view(), name='catalog_crear'),
    path('gestion/<slug:entidad>/<int:pk>/', cv.Detalle.as_view(), name='catalog_detalle'),
    path('gestion/<slug:entidad>/<int:pk>/editar/', cv.Editar.as_view(), name='catalog_editar'),
    path('gestion/<slug:entidad>/<int:pk>/eliminar/', cv.Borrar.as_view(), name='catalog_borrar'),
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('buscar/', BusquedaGlobalView.as_view(), name='buscar'),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('organizacion/', include('organizacion.urls')),
    path('actividades/', include('actividades.urls')),
    path('agenda/', include('agenda.urls')),
    path('resultados/', include('resultados.urls')),
]
