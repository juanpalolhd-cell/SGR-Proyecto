from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from sgr.domain import DomainMixin
from django.utils import timezone

from organizacion.models import Persona


class Periodo(DomainMixin, models.Model):
    codigo = models.CharField(max_length=30, unique=True, null=True, blank=True)
    anio = models.PositiveIntegerField(default=2026, validators=[MinValueValidator(1900), MaxValueValidator(9999)])
    numero = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(4)])
    nombre = models.CharField(max_length=100)
    inicio = models.DateField()
    termino = models.DateField()
    dias_computables = models.PositiveIntegerField()
    estado = models.CharField(max_length=50, default="Abierto")

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(numero__gte=1, numero__lte=4), name="trimestre_numero_1_4"), models.CheckConstraint(condition=models.Q(termino__gte=models.F("inicio")), name="trimestre_fechas_ordenadas")]
        ordering = ["-inicio"]
        verbose_name = "Período"
        verbose_name_plural = "Períodos"

    def __str__(self):
        return self.nombre


class Meta(DomainMixin, models.Model):
    catalogo = models.ForeignKey("CatalogoMeta", null=True, blank=True, on_delete=models.PROTECT, related_name="asignaciones")
    fecha_asignacion = models.DateField(default=timezone.localdate)
    observacion = models.TextField(blank=True)
    estado = models.BooleanField(default=True)
    periodo = models.ForeignKey("Periodo", on_delete=models.PROTECT, related_name="metas")
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="metas")
    item = models.CharField(max_length=120)
    unidad = models.CharField(max_length=80)
    meta = models.DecimalField("Cantidad objetivo", max_digits=10, decimal_places=2, default=1, validators=[MinValueValidator(Decimal("0.01"))])
    avance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ponderador = models.DecimalField("Ponderación", max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(meta__gt=0), name="asignacion_objetivo_positivo"), models.CheckConstraint(condition=models.Q(ponderador__gte=0, ponderador__lte=100), name="asignacion_ponderacion_0_100")]
        ordering = ["periodo", "persona", "item"]
        verbose_name = "Meta"
        verbose_name_plural = "Metas"

    def __str__(self):
        return f"{self.item} ({self.persona})"


class CatalogoMeta(DomainMixin, models.Model):
    codigo = models.CharField(max_length=30, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField()
    tipo = models.CharField(max_length=30, choices=[("individual", "Individual"), ("colectiva", "Colectiva")])
    unidad_medida = models.CharField(max_length=80)
    requiere_evidencia = models.BooleanField(default=False)
    estado = models.BooleanField(default=True)
    def __str__(self): return self.nombre
