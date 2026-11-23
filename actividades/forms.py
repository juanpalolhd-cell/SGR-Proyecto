from django import forms

from .models import Actividad, Evidencia


class ActividadForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = [
            "codigo",
            "fecha",
            "descripcion",
            "accion",
            "contacto",
            "telefono",
            "persona",
            "unidad",
            "item",
            "estado",
            "agenda",
        ]
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "campo"}),
            "fecha": forms.DateInput(attrs={"class": "campo", "type": "date"}),
            "descripcion": forms.Textarea(attrs={"class": "campo", "rows": 3}),
            "accion": forms.TextInput(attrs={"class": "campo"}),
            "contacto": forms.TextInput(attrs={"class": "campo"}),
            "telefono": forms.TextInput(attrs={"class": "campo"}),
            "persona": forms.Select(attrs={"class": "campo"}),
            "unidad": forms.Select(attrs={"class": "campo"}),
            "item": forms.TextInput(attrs={"class": "campo"}),
            "estado": forms.TextInput(attrs={"class": "campo"}),
            "agenda": forms.CheckboxInput(attrs={"class": "campo-check"}),
        }


class EvidenciaForm(forms.ModelForm):
    class Meta:
        model = Evidencia
        fields = [
            "codigo",
            "actividad",
            "ruta",
            "autor",
            "fecha",
            "estado",
            "verificador",
            "observacion",
        ]
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "campo"}),
            "actividad": forms.Select(attrs={"class": "campo"}),
            "ruta": forms.TextInput(attrs={"class": "campo"}),
            "autor": forms.TextInput(attrs={"class": "campo"}),
            "fecha": forms.DateInput(attrs={"class": "campo", "type": "date"}),
            "estado": forms.TextInput(attrs={"class": "campo"}),
            "verificador": forms.TextInput(attrs={"class": "campo"}),
            "observacion": forms.Textarea(attrs={"class": "campo", "rows": 3}),
        }
