"""Compatibility routes use the same validated canonical CRUD, never a second write path."""
from . import catalog_views


def crud(request, entidad, accion, **kwargs):
    params={'entidad':entidad}
    if kwargs: params['pk']=next(iter(kwargs.values()))
    view={'crear':catalog_views.Crear,'editar':catalog_views.Editar,'borrar':catalog_views.Borrar}[accion]
    return view.as_view()(request,**params)
