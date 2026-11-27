"""V4.3: solicitudes de vecinos con flujo de supervisión, derivación a empresa y verificación."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from organizacion.models import Empresa, JuntaVecinos, Persona, Vecino
from sgr.domain import DomainMixin
from sgr.parametros import parametros
from sgr.reglas import validar_periodo_abierto

INGRESADA = "Ingresada"
SUPERVISION = "En supervisión/verificación"
DERIVADA = "Derivada a empresa"
EJECUCION = "En ejecución"
VERIFICACION = "Verificación de realizado"
CERRADA = "Cerrada"
RECHAZADA = "Rechazada"
ANULADA = "Anulada"

ESTADOS_SOLICITUD = [
    (INGRESADA, "Ingresada"),
    (SUPERVISION, "En supervisión/verificación"),
    (DERIVADA, "Derivada a empresa"),
    (EJECUCION, "En ejecución"),
    (VERIFICACION, "Verificación de realizado"),
    (CERRADA, "Cerrada"),
    (RECHAZADA, "Rechazada"),
    (ANULADA, "Anulada"),
]
# Avance de un paso a la vez; los retrocesos (devolver) exigen observación.
FLUJO = [INGRESADA, SUPERVISION, DERIVADA, EJECUCION, VERIFICACION, CERRADA]
TRANSICIONES = {
    INGRESADA: [SUPERVISION, RECHAZADA, ANULADA],
    SUPERVISION: [DERIVADA, INGRESADA, RECHAZADA, ANULADA],
    DERIVADA: [EJECUCION, SUPERVISION, ANULADA],
    EJECUCION: [VERIFICACION, DERIVADA, ANULADA],
    VERIFICACION: [CERRADA, EJECUCION],
    CERRADA: [],
    RECHAZADA: [],
    ANULADA: [],
}
TERMINALES = {CERRADA, RECHAZADA, ANULADA}
NO_CUENTAN = {RECHAZADA, ANULADA}
PORCENTAJES_POR_DEFECTO = {INGRESADA: 10, SUPERVISION: 25, DERIVADA: 50, EJECUCION: 75, VERIFICACION: 90, CERRADA: 100, RECHAZADA: 0, ANULADA: 0}


def porcentaje_estado(estado, params=None):
    tabla = dict(PORCENTAJES_POR_DEFECTO)
    try:
        tabla.update((params or parametros()).get("solicitud_avance") or {})
    except (AttributeError, TypeError, ValueError):
        pass
    if estado in NO_CUENTAN:
        return 0
    try:
        return max(0, min(100, int(tabla.get(estado, 0))))
    except (TypeError, ValueError):
        return PORCENTAJES_POR_DEFECTO.get(estado, 0)


def es_retroceso(actual, nuevo):
    return actual in FLUJO and nuevo in FLUJO and FLUJO.index(nuevo) < FLUJO.index(actual)


def requiere_observacion(actual, nuevo):
    return es_retroceso(actual, nuevo) or nuevo in NO_CUENTAN


class Solicitud(DomainMixin, models.Model):
    codigo = models.CharField(max_length=30, unique=True, null=True, blank=True)
    fecha_ingreso = models.DateField(default=timezone.localdate)
    vecino = models.ForeignKey(Vecino, on_delete=models.PROTECT, related_name="solicitudes")
    junta = models.ForeignKey(JuntaVecinos, null=True, blank=True, on_delete=models.PROTECT, related_name="solicitudes", verbose_name="JJVV al ingresar")
    cargo_jjvv = models.CharField("Cargo en la JJVV al ingresar", max_length=120, blank=True)
    asunto = models.CharField(max_length=200)
    descripcion = models.TextField("Descripción")
    responsable = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="solicitudes", verbose_name="Funcionario responsable")
    asignacion = models.ForeignKey("resultados.Meta", null=True, blank=True, on_delete=models.PROTECT, related_name="solicitudes", verbose_name="Asignación de meta")
    empresa = models.ForeignKey(Empresa, null=True, blank=True, on_delete=models.PROTECT, related_name="solicitudes", verbose_name="Empresa contratista")
    fecha_comprometida = models.DateField(null=True, blank=True)
    fecha_cierre = models.DateField(null=True, blank=True, editable=False)
    estado = models.CharField(max_length=40, choices=ESTADOS_SOLICITUD, default=INGRESADA)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ["-fecha_ingreso", "-id"]
        verbose_name = "Solicitud"
        verbose_name_plural = "Solicitudes"

    def __str__(self):
        return f"{self.codigo or 'Solicitud'} · {self.asunto}"

    @property
    def porcentaje(self):
        return porcentaje_estado(self.estado)

    @property
    def estados_siguientes(self):
        return TRANSICIONES.get(self.estado, [])

    def clean(self):
        super().clean()
        errors = {}
        if self.fecha_comprometida and self.fecha_ingreso and self.fecha_comprometida < self.fecha_ingreso:
            errors["fecha_comprometida"] = "La fecha comprometida no puede ser anterior a la fecha de ingreso."
        if self.asignacion_id and self.responsable_id and self.asignacion.persona_id != self.responsable_id:
            errors["asignacion"] = "La asignación debe ser del funcionario responsable."
        if self.estado in (DERIVADA, EJECUCION, VERIFICACION) and not self.empresa_id:
            errors["empresa"] = "Indique la empresa contratista a la que se deriva la solicitud."
        if errors:
            raise ValidationError(errors)
        validar_periodo_abierto(self)


class HistorialSolicitud(models.Model):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name="historial")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    fecha = models.DateTimeField(default=timezone.now)
    estado_anterior = models.CharField(max_length=40, blank=True)
    estado_nuevo = models.CharField(max_length=40)
    porcentaje = models.PositiveSmallIntegerField(default=0)
    observacion = models.TextField(blank=True)

    class Meta:
        ordering = ["fecha", "id"]
        verbose_name = "Historial de solicitud"
        verbose_name_plural = "Historial de solicitudes"

    def __str__(self):
        return f"{self.solicitud_id}: {self.estado_anterior or '—'} → {self.estado_nuevo}"
