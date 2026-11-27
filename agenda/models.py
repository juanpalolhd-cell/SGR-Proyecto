from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from sgr.domain import DomainMixin

from organizacion.models import Persona, Unidad


ESTADO_INGRESADO = "Ingresado"
ESTADO_PENDIENTE = "Pendiente"
ESTADO_EN_PROCESO = "En proceso"
ESTADO_REALIZADO = "Realizado"
ESTADOS_COMPROMISO = [
    (ESTADO_INGRESADO, "Ingresado"),
    (ESTADO_PENDIENTE, "Pendiente"),
    (ESTADO_EN_PROCESO, "En proceso"),
    (ESTADO_REALIZADO, "Realizado"),
]
# Transiciones controladas del tubo de trabajo (RF-018). Reabrir un realizado exige observación.
TRANSICIONES = {
    ESTADO_INGRESADO: {ESTADO_PENDIENTE, ESTADO_EN_PROCESO},
    ESTADO_PENDIENTE: {ESTADO_EN_PROCESO, ESTADO_REALIZADO},
    ESTADO_EN_PROCESO: {ESTADO_PENDIENTE, ESTADO_REALIZADO},
    ESTADO_REALIZADO: {ESTADO_EN_PROCESO},
}
ESTADOS_INICIALES = (ESTADO_INGRESADO, ESTADO_PENDIENTE)

PLAZO_ETIQUETAS = {
    "vencido": "Vencido",
    "proximo": "Próximo a vencer",
    "al_dia": "En plazo",
    "realizado": "Realizado",
    "fuera_plazo": "Realizado fuera de plazo",
}


class Compromiso(DomainMixin, models.Model):
    origen = models.CharField(max_length=120)
    solicitante = models.CharField(max_length=150)
    territorio = models.CharField(max_length=150)
    responsable = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="compromisos")
    unidad = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="compromisos")
    area_apoyo = models.CharField(max_length=120)
    fecha_comprometida = models.DateField()
    estado = models.CharField(max_length=50, choices=ESTADOS_COMPROMISO, default=ESTADO_INGRESADO)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ["fecha_comprometida", "id"]
        verbose_name = "Compromiso"
        verbose_name_plural = "Compromisos"

    def __str__(self):
        return f"{self.territorio} - {self.estado}"

    def clean(self):
        super().clean()
        anterior = None
        if self.pk:
            anterior = type(self).objects.filter(pk=self.pk).values_list("estado", flat=True).first()
        if anterior is None:
            if self.estado not in ESTADOS_INICIALES:
                raise ValidationError({"estado": "Un compromiso nuevo debe comenzar como Ingresado o Pendiente."})
        elif anterior != self.estado and self.estado not in TRANSICIONES.get(anterior, set()):
            permitidos = ", ".join(sorted(TRANSICIONES.get(anterior, set()))) or "ninguno"
            raise ValidationError({"estado": f"Transición no permitida: de «{anterior}» a «{self.estado}». Desde «{anterior}» puede pasar a: {permitidos}."})

    def fecha_realizado(self):
        ultimo = self.historial.filter(estado_nuevo=ESTADO_REALIZADO).order_by("-fecha", "-id").first()
        return timezone.localtime(ultimo.fecha).date() if ultimo else None

    def situacion_plazo(self, hoy=None, dias_aviso=7):
        """vencido, proximo, al_dia, realizado o fuera_plazo (RF-019)."""
        hoy = hoy or timezone.localdate()
        if self.estado == ESTADO_REALIZADO:
            cierre = self.fecha_realizado()
            return "fuera_plazo" if cierre and cierre > self.fecha_comprometida else "realizado"
        if self.fecha_comprometida < hoy:
            return "vencido"
        if self.fecha_comprometida <= hoy + timedelta(days=int(dias_aviso)):
            return "proximo"
        return "al_dia"


class HistorialEstado(models.Model):
    """Cada cambio de estado (o de fecha comprometida) del tubo de trabajo: quién, cuándo, de qué estado a cuál."""
    compromiso = models.ForeignKey(Compromiso, on_delete=models.CASCADE, related_name="historial")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="cambios_compromiso")
    fecha = models.DateTimeField(default=timezone.now)
    estado_anterior = models.CharField(max_length=50, blank=True)
    estado_nuevo = models.CharField(max_length=50)
    observacion = models.TextField(blank=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "Historial de estado"
        verbose_name_plural = "Historial de estados"

    def __str__(self):
        return f"{self.compromiso_id}: {self.estado_anterior or '—'} → {self.estado_nuevo}"


class Hito(DomainMixin, models.Model):
    codigo = models.CharField(max_length=30, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField()
    periodicidad = models.CharField(max_length=20, choices=[("unico", "Único"), ("mensual", "Mensual"), ("trimestral", "Trimestral"), ("anual", "Anual")])
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField()
    delegacion = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="hitos")
    territorio = models.ForeignKey("organizacion.Territorio", on_delete=models.PROTECT, related_name="hitos")
    responsables = models.ManyToManyField(Persona, related_name="hitos")
    estado = models.BooleanField(default=True)
    def __str__(self): return self.nombre
