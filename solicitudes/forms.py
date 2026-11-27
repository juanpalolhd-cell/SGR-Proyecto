from django import forms
from django.db.models import Q

from organizacion.models import Empresa, Persona, Vecino, resumen_jjvv
from resultados.models import Meta

from .models import DERIVADA, ESTADOS_SOLICITUD, Solicitud, TRANSICIONES, porcentaje_estado, requiere_observacion


class SolicitudForm(forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = ["fecha_ingreso", "vecino", "asunto", "descripcion", "responsable", "asignacion", "empresa", "fecha_comprometida", "observaciones"]
        widgets = {
            "fecha_ingreso": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "fecha_comprometida": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }
        help_texts = {
            "vecino": "Al elegir el vecino se consulta si pertenece a una junta de vecinos y su cargo.",
            "asignacion": "Opcional. Si se indica, la solicitud cerrada suma al avance calculado de esa meta del funcionario.",
            "empresa": "Obligatoria al derivar la solicitud a la empresa.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "campo")
        self.fields["vecino"].queryset = Vecino.objects.filter(Q(estado=True) | Q(pk=self.instance.vecino_id or 0)).order_by("apellidos", "nombres")
        self.fields["responsable"].queryset = Persona.objects.order_by("nombre")
        self.fields["asignacion"].queryset = Meta.objects.filter(estado=True).select_related("persona", "periodo").order_by("periodo", "persona")
        self.fields["empresa"].queryset = Empresa.objects.filter(Q(estado=True) | Q(pk=self.instance.empresa_id or 0))
        if self.instance.pk:
            self.fields["vecino"].disabled = True
            self.fields["vecino"].help_text = "El vecino no se cambia después de ingresar la solicitud (la consulta JJVV quedó registrada al ingresar)."
        self.jjvv = None

    def clean(self):
        data = super().clean()
        vecino = data.get("vecino")
        if vecino and not self.instance.pk:
            self.jjvv = resumen_jjvv(vecino)
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        if not obj.pk and self.jjvv is not None:
            obj.junta = self.jjvv["junta"]
            obj.cargo_jjvv = self.jjvv["cargo"]
        if commit:
            obj.save()
        return obj


class CambioEstadoForm(forms.Form):
    nuevo_estado = forms.ChoiceField(label="Pasar a", widget=forms.Select(attrs={"class": "campo"}))
    empresa = forms.ModelChoiceField(label="Empresa contratista", queryset=Empresa.objects.filter(estado=True), required=False, widget=forms.Select(attrs={"class": "campo"}), help_text="Requerida al derivar a la empresa.")
    observacion = forms.CharField(label="Observación", required=False, widget=forms.Textarea(attrs={"class": "campo", "rows": 2}), help_text="Obligatoria al devolver a una etapa anterior, rechazar o anular.")

    def __init__(self, solicitud, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.solicitud = solicitud
        etiquetas = dict(ESTADOS_SOLICITUD)
        self.fields["nuevo_estado"].choices = [(e, f"{etiquetas[e]} ({porcentaje_estado(e)} %)") for e in TRANSICIONES.get(solicitud.estado, [])]
        if solicitud.empresa_id:
            self.fields["empresa"].initial = solicitud.empresa_id

    def clean(self):
        data = super().clean()
        nuevo = data.get("nuevo_estado")
        if nuevo and requiere_observacion(self.solicitud.estado, nuevo) and not (data.get("observacion") or "").strip():
            self.add_error("observacion", "La observación es obligatoria para devolver, rechazar o anular.")
        if nuevo == DERIVADA and not (data.get("empresa") or self.solicitud.empresa_id):
            self.add_error("empresa", "Indique la empresa contratista.")
        return data
