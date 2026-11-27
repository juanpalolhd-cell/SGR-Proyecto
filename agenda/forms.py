from django import forms

from .models import (
    Compromiso,
    ESTADO_REALIZADO,
    ESTADOS_COMPROMISO,
    ESTADOS_INICIALES,
    HistorialEstado,
    TRANSICIONES,
)


class CompromisoForm(forms.ModelForm):
    observacion_cambio = forms.CharField(
        label="Observación del cambio",
        required=False,
        widget=forms.Textarea(attrs={"class": "campo", "rows": 2}),
        help_text="Obligatoria al reabrir un compromiso realizado o al cambiar la fecha comprometida (indique el motivo). Queda en el historial.",
    )

    class Meta:
        model = Compromiso
        fields = [
            "origen",
            "solicitante",
            "territorio",
            "responsable",
            "unidad",
            "area_apoyo",
            "fecha_comprometida",
            "estado",
            "observaciones",
        ]
        labels = {"unidad": "Delegación", "area_apoyo": "Área de apoyo"}
        widgets = {
            "origen": forms.TextInput(attrs={"class": "campo"}),
            "solicitante": forms.TextInput(attrs={"class": "campo"}),
            "territorio": forms.TextInput(attrs={"class": "campo"}),
            "responsable": forms.Select(attrs={"class": "campo"}),
            "unidad": forms.Select(attrs={"class": "campo"}),
            "area_apoyo": forms.TextInput(attrs={"class": "campo"}),
            "fecha_comprometida": forms.DateInput(format="%Y-%m-%d", attrs={"class": "campo", "type": "date"}),
            "estado": forms.Select(attrs={"class": "campo"}),
            "observaciones": forms.Textarea(attrs={"class": "campo", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._estado_original = self.instance.estado if self.instance.pk else ""
        self._fecha_original = self.instance.fecha_comprometida if self.instance.pk else None
        if self.instance.pk:
            permitidos = {self._estado_original} | TRANSICIONES.get(self._estado_original, set())
        else:
            permitidos = set(ESTADOS_INICIALES)
        self.fields["estado"].choices = [(v, e) for v, e in ESTADOS_COMPROMISO if v in permitidos]
        self.fields["estado"].help_text = "Solo se muestran los estados permitidos desde el estado actual."

    def clean(self):
        data = super().clean()
        obs = (data.get("observacion_cambio") or "").strip()
        if self.instance.pk:
            if self._estado_original == ESTADO_REALIZADO and data.get("estado") and data["estado"] != ESTADO_REALIZADO and not obs:
                self.add_error("observacion_cambio", "Indique por qué se reabre un compromiso ya realizado.")
            nueva_fecha = data.get("fecha_comprometida")
            if nueva_fecha and self._fecha_original and nueva_fecha != self._fecha_original and not obs:
                self.add_error("observacion_cambio", "Indique el motivo del cambio de fecha comprometida (comunicación del incumplimiento del plazo).")
        return data

    def registrar_historial(self, usuario):
        """Crea las entradas de historial después de guardar. Devuelve cuántas creó."""
        obj = self.instance
        obs = (self.cleaned_data.get("observacion_cambio") or "").strip()
        usuario = usuario if getattr(usuario, "is_authenticated", False) else None
        creadas = 0
        if not self._estado_original:
            HistorialEstado.objects.create(compromiso=obj, usuario=usuario, estado_anterior="", estado_nuevo=obj.estado, observacion=obs or "Registro inicial del compromiso.")
            return 1
        if obj.estado != self._estado_original:
            HistorialEstado.objects.create(compromiso=obj, usuario=usuario, estado_anterior=self._estado_original, estado_nuevo=obj.estado, observacion=obs)
            creadas += 1
        if self._fecha_original and obj.fecha_comprometida != self._fecha_original:
            texto = f"Cambio de fecha comprometida: {self._fecha_original:%d-%m-%Y} → {obj.fecha_comprometida:%d-%m-%Y}. Motivo: {obs}"
            HistorialEstado.objects.create(compromiso=obj, usuario=usuario, estado_anterior=obj.estado, estado_nuevo=obj.estado, observacion=texto)
            creadas += 1
        return creadas
