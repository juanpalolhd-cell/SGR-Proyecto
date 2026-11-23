"""Shared identifiers and server-side cross-field validation."""
import uuid
from django.core.exceptions import ValidationError

class DomainMixin:
    def save(self, *args, **kwargs):
        if hasattr(self, "codigo") and not self.codigo:
            self.codigo = self._meta.model_name[:5].upper() + "-" + uuid.uuid4().hex[:18]
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        errors = {}
        for start, end in (("inicio", "termino"), ("fecha_inicio", "fecha_termino"), ("fecha", "fecha_compromiso"), ("fecha_ingreso", "fecha_atencion")):
            a, b = getattr(self, start, None), getattr(self, end, None)
            if a and b and b < a:
                errors[end] = "La fecha final no puede ser anterior a la fecha inicial."
        territory = getattr(self, "territorio", None) if getattr(self, "territorio_id", None) else None
        delegation_id = getattr(self, "delegacion_id", None) or getattr(self, "unidad_id", None)
        if territory and delegation_id and territory.delegacion_id != delegation_id:
            errors["territorio"] = "El territorio no pertenece a la delegación seleccionada."
        if errors:
            raise ValidationError(errors)
