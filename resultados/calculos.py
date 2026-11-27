"""Cálculos de resultados según las reglas del cliente (guía SGR, sección 7)."""
from datetime import date

from django.utils import timezone

from sgr.reglas import evidencia_aprobada, normalizar

# Estados de actividad que la guía considera "válidos" para el avance (RN-003).
ESTADOS_ACTIVIDAD_VALIDOS = {"validada", "validado", "aprobada", "aprobado", "realizada", "realizado"}


def avance_calculado(meta):
    """RN-003 + RN-009: cuenta actividades válidas y gestiones atendidas de la asignación dentro del período.

    Si el catálogo exige evidencia, cada registro cuenta solo con al menos una evidencia Aprobada;
    las rechazadas o anuladas nunca cuentan. Devuelve (cantidad, detalle).
    """
    periodo = meta.periodo
    exige = bool(meta.catalogo_id and meta.catalogo.requiere_evidencia)
    detalle = {"actividades": 0, "gestiones": 0, "sin_evidencia": 0, "exige_evidencia": exige}

    def cuenta(registro):
        if not exige:
            return True
        return any(evidencia_aprobada(e) for e in registro.evidencias.all())

    actividades = meta.actividades_asignadas.filter(fecha__gte=periodo.inicio, fecha__lte=periodo.termino).prefetch_related("evidencias")
    for a in actividades:
        if normalizar(a.estado) in ESTADOS_ACTIVIDAD_VALIDOS:
            if cuenta(a):
                detalle["actividades"] += 1
            else:
                detalle["sin_evidencia"] += 1
    gestiones = meta.gestiones.filter(estado="atendida", fecha_atencion__gte=periodo.inicio, fecha_atencion__lte=periodo.termino).prefetch_related("evidencias")
    for g in gestiones:
        if cuenta(g):
            detalle["gestiones"] += 1
        else:
            detalle["sin_evidencia"] += 1
    return detalle["actividades"] + detalle["gestiones"], detalle


def meta_esperada(periodo, hoy=None):
    """RN-007: días transcurridos / días totales del período x 100, con la fecha real.

    Se cuentan días corridos incluyendo inicio y término; antes del inicio es 0 % y después del término 100 %.
    """
    if periodo is None:
        return 0.0
    hoy = hoy or timezone.localdate()
    total = (periodo.termino - periodo.inicio).days + 1
    if total <= 0 or hoy < periodo.inicio:
        return 0.0
    transcurridos = min((hoy - periodo.inicio).days + 1, total)
    return round(transcurridos / total * 100, 1)


def periodo_vigente(periodos, hoy=None):
    hoy = hoy or timezone.localdate()
    for p in periodos:
        if p.inicio <= hoy <= p.termino:
            return p
    return None
