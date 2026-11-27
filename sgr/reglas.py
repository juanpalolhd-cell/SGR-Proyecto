"""Reglas de negocio transversales del cliente (guía SGR, sección 7)."""
import unicodedata

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# Teléfono: + opcional, luego 8 a 16 caracteres entre dígitos, espacios o guiones. Ej.: +56 9 1234 5678
validar_telefono = RegexValidator(
    regex=r"^\+?[0-9][0-9 \-]{7,15}$",
    message="Ingrese un teléfono válido, por ejemplo +56 9 1234 5678 (solo dígitos, espacios o guiones; mínimo 8 dígitos).",
    code="telefono_invalido",
)


def normalizar(texto):
    """Minúsculas y sin tildes, para comparar estados escritos a mano."""
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return " ".join(texto.lower().replace("_", " ").split())


def periodo_cerrado(periodo):
    return bool(periodo) and normalizar(periodo.estado).startswith("cerrad")


def evidencia_aprobada(evidencia):
    return normalizar(evidencia.estado).startswith("aprobad")


def _periodos_cerrados_por_fecha(fecha):
    from resultados.models import Periodo
    if not fecha:
        return []
    return [p for p in Periodo.objects.filter(inicio__lte=fecha, termino__gte=fecha) if periodo_cerrado(p)]


def periodos_cerrados_de(obj):
    """Períodos cerrados a los que pertenece un registro (RN-013)."""
    from actividades.models import Actividad, Evidencia, GestionSocial
    from resultados.models import Meta
    encontrados = []
    if isinstance(obj, Meta):
        periodo = obj.periodo if obj.periodo_id else None
        if periodo_cerrado(periodo):
            encontrados.append(periodo)
    elif isinstance(obj, Actividad):
        if obj.asignacion_id and periodo_cerrado(obj.asignacion.periodo):
            encontrados.append(obj.asignacion.periodo)
        encontrados += _periodos_cerrados_por_fecha(obj.fecha)
    elif isinstance(obj, GestionSocial):
        if obj.asignacion_id and periodo_cerrado(obj.asignacion.periodo):
            encontrados.append(obj.asignacion.periodo)
        encontrados += _periodos_cerrados_por_fecha(obj.fecha_atencion)
    elif type(obj).__name__ == "Solicitud" and type(obj)._meta.app_label == "solicitudes":
        # V4.3: una solicitud queda bloqueada si su asignación es de un período cerrado
        # o si se cerró dentro de un período cerrado.
        if obj.asignacion_id and periodo_cerrado(obj.asignacion.periodo):
            encontrados.append(obj.asignacion.periodo)
        encontrados += _periodos_cerrados_por_fecha(obj.fecha_cierre)
    elif isinstance(obj, Evidencia):
        if obj.actividad_id:
            encontrados += periodos_cerrados_de(obj.actividad)
        if obj.gestion_social_id:
            encontrados += periodos_cerrados_de(obj.gestion_social)
    unicos = []
    for p in encontrados:
        if p not in unicos:
            unicos.append(p)
    return unicos


def mensaje_periodo_cerrado(periodos):
    nombres = ", ".join(str(p) for p in periodos)
    return f"El período {nombres} está cerrado: sus datos no se pueden crear, modificar ni eliminar (RN-013). Solo un usuario con Acceso total puede reabrirlo."


def validar_periodo_abierto(obj):
    """Se llama desde clean(): revisa el estado nuevo y el guardado en la base."""
    cerrados = periodos_cerrados_de(obj)
    if obj.pk:
        original = type(obj).objects.filter(pk=obj.pk).first()
        if original is not None:
            cerrados += [p for p in periodos_cerrados_de(original) if p not in cerrados]
    if cerrados:
        raise ValidationError(mensaje_periodo_cerrado(cerrados))


def es_acceso_total(user):
    return bool(user and user.is_authenticated and user.is_active and (user.is_superuser or user.groups.filter(name="Acceso total").exists()))
