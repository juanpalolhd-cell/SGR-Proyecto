"""Cambio de estado de solicitudes: un paso a la vez, con historial (V4.3)."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import CERRADA, HistorialSolicitud, TRANSICIONES, porcentaje_estado, requiere_observacion


@transaction.atomic
def cambiar_estado(solicitud, nuevo, usuario=None, observacion="", empresa=None):
    actual = solicitud.estado
    observacion = (observacion or "").strip()
    if nuevo not in TRANSICIONES.get(actual, []):
        raise ValidationError(f"No se puede pasar de «{actual}» a «{nuevo}». Solo se avanza un paso a la vez.")
    if requiere_observacion(actual, nuevo) and not observacion:
        raise ValidationError("Indique una observación: es obligatoria al devolver la solicitud a una etapa anterior, rechazarla o anularla.")
    previo = (solicitud.estado, solicitud.empresa_id, solicitud.fecha_cierre)
    if empresa is not None:
        solicitud.empresa = empresa
    solicitud.estado = nuevo
    solicitud.fecha_cierre = timezone.localdate() if nuevo == CERRADA else None
    try:
        solicitud.full_clean()
    except ValidationError:
        # Deja el objeto en memoria como estaba si el cambio no es válido.
        solicitud.estado, solicitud.empresa_id, solicitud.fecha_cierre = previo
        raise
    solicitud.save()
    usuario = usuario if getattr(usuario, "is_authenticated", False) else None
    return HistorialSolicitud.objects.create(solicitud=solicitud, usuario=usuario, estado_anterior=actual, estado_nuevo=nuevo, porcentaje=porcentaje_estado(nuevo), observacion=observacion)
