from django.db import models
from sgr.domain import DomainMixin

from organizacion.models import Persona, Unidad


class Compromiso(DomainMixin, models.Model):
    origen = models.CharField(max_length=120)
    solicitante = models.CharField(max_length=150)
    territorio = models.CharField(max_length=150)
    responsable = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="compromisos")
    unidad = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="compromisos")
    area_apoyo = models.CharField(max_length=120)
    fecha_comprometida = models.DateField()
    estado = models.CharField(max_length=50)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ["fecha_comprometida", "id"]
        verbose_name = "Compromiso"
        verbose_name_plural = "Compromisos"

    def __str__(self):
        return f"{self.territorio} - {self.estado}"


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
