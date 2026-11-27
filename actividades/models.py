from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from sgr.domain import DomainMixin
from sgr.reglas import validar_periodo_abierto, validar_telefono

from organizacion.models import Persona, Unidad


class Actividad(DomainMixin, models.Model):
    asignacion = models.ForeignKey("resultados.Meta", null=True, blank=True, on_delete=models.PROTECT, related_name="actividades_asignadas")
    hito = models.ForeignKey("agenda.Hito", null=True, blank=True, on_delete=models.PROTECT, related_name="actividades")
    tipo = models.CharField(max_length=30, default="gestion", choices=[("gestion", "Gestión"), ("visita", "Visita"), ("reunion", "Reunión"), ("otro", "Otro")])
    origen = models.CharField(max_length=150, blank=True)
    solicitante = models.ForeignKey("organizacion.Vecino", null=True, blank=True, on_delete=models.PROTECT, related_name="actividades")
    territorio = models.ForeignKey("organizacion.Territorio", null=True, blank=True, on_delete=models.PROTECT, related_name="actividades")
    responsable = models.ForeignKey(Persona, null=True, blank=True, on_delete=models.PROTECT, related_name="actividades_responsable")
    fecha_compromiso = models.DateField(null=True, blank=True)
    apoyo = models.CharField(max_length=150, blank=True)
    avance = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    resultado = models.TextField(blank=True)

    def clean(self):
        super().clean()
        errors = {}
        if self.persona_id and self.unidad_id and self.persona.delegacion_id != self.unidad_id:
            errors["persona"] = "El funcionario no pertenece a la delegación seleccionada."
        if self.asignacion_id and self.persona_id and self.asignacion.persona_id != self.persona_id:
            errors["asignacion"] = "La asignación no corresponde al funcionario seleccionado."
        if self.hito_id and self.territorio_id and self.hito.territorio_id != self.territorio_id:
            errors["hito"] = "El hito debe corresponder al territorio seleccionado."
        if self.solicitante_id and self.territorio_id and self.solicitante.territorio_id != self.territorio_id:
            errors["solicitante"] = "El solicitante debe corresponder al territorio seleccionado."
        if errors: raise ValidationError(errors)
        validar_periodo_abierto(self)

    codigo = models.CharField(max_length=50, unique=True)
    fecha = models.DateField()
    descripcion = models.TextField()
    accion = models.CharField(max_length=200)
    contacto = models.CharField(max_length=120)
    telefono = models.CharField(max_length=80, blank=True, validators=[validar_telefono])
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="actividades")
    unidad = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="actividades")
    item = models.CharField(max_length=120)
    estado = models.CharField(max_length=50)
    agenda = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fecha", "codigo"]
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"

    def __str__(self):
        return self.codigo


class Evidencia(DomainMixin, models.Model):
    gestion_social = models.ForeignKey("GestionSocial", null=True, blank=True, on_delete=models.PROTECT, related_name="evidencias")
    tipo = models.CharField(max_length=30, default="referencia", choices=[("referencia", "Referencia"), ("fotografia", "Fotografía"), ("documento", "Documento")])
    autor_usuario = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.PROTECT, related_name="evidencias_autoria")
    verificador_usuario = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.PROTECT, related_name="evidencias_verificacion")

    def clean(self):
        super().clean()
        if bool(self.actividad_id) == bool(self.gestion_social_id):
            raise ValidationError("Seleccione exactamente un origen: actividad o gestión social.")
        validar_periodo_abierto(self)

    codigo = models.CharField(max_length=50, unique=True)
    actividad = models.ForeignKey("Actividad", null=True, blank=True, on_delete=models.PROTECT, related_name="evidencias")
    ruta = models.CharField(max_length=200)
    autor = models.CharField(max_length=120)
    fecha = models.DateField()
    estado = models.CharField(max_length=50)
    verificador = models.CharField(max_length=120, blank=True)
    observacion = models.TextField(blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=(models.Q(actividad__isnull=False, gestion_social__isnull=True) | models.Q(actividad__isnull=True, gestion_social__isnull=False)), name="evidencia_un_solo_origen")]
        ordering = ["-fecha", "codigo"]
        verbose_name = "Evidencia"
        verbose_name_plural = "Evidencias"

    def __str__(self):
        return self.codigo


class GestionSocial(DomainMixin, models.Model):
    fecha_ingreso = models.DateField()
    fecha_atencion = models.DateField()
    beneficiario = models.ForeignKey("organizacion.Vecino", on_delete=models.PROTECT, related_name="gestiones")
    tipo = models.ForeignKey("organizacion.TipoAtencion", on_delete=models.PROTECT, related_name="gestiones")
    subtipo = models.ForeignKey("organizacion.SubAtencion", on_delete=models.PROTECT, related_name="gestiones")
    asignacion = models.ForeignKey("resultados.Meta", on_delete=models.PROTECT, related_name="gestiones")
    visita = models.BooleanField(default=False)
    actuaciones = models.TextField()
    derivacion = models.CharField(max_length=200, blank=True)
    informe = models.TextField(blank=True)
    beneficio = models.CharField(max_length=200, blank=True)
    resultado = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=[("pendiente", "Pendiente"), ("atendida", "Atendida"), ("anulada", "Anulada")], default="pendiente")
    MAX_GESTIONES_POR_PERSONA = 3
    def __str__(self): return f"Gestión {self.pk or 'nueva'} — {self.beneficiario}"
    def clean(self):
        super().clean()
        if self.subtipo_id and self.tipo_id and self.subtipo.tipo_atencion_id != self.tipo_id:
            raise ValidationError({"subtipo": "El subtipo no pertenece al tipo seleccionado."})
        # RN-012: hasta tres gestiones (no anuladas) por persona usuaria.
        if self.beneficiario_id and self.estado != "anulada":
            otras = GestionSocial.objects.filter(beneficiario_id=self.beneficiario_id).exclude(estado="anulada")
            if self.pk:
                otras = otras.exclude(pk=self.pk)
            original = GestionSocial.objects.filter(pk=self.pk).values("beneficiario_id", "estado").first() if self.pk else None
            suma_nueva = original is None or original["beneficiario_id"] != self.beneficiario_id or original["estado"] == "anulada"
            if suma_nueva and otras.count() >= self.MAX_GESTIONES_POR_PERSONA:
                raise ValidationError({"beneficiario": f"Esta persona ya tiene {otras.count()} gestiones activas; el máximo es {self.MAX_GESTIONES_POR_PERSONA} (RN-012). Anule o complete una gestión existente."})
        validar_periodo_abierto(self)
