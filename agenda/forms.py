from django import forms

from .models import Compromiso


class CompromisoForm(forms.ModelForm):
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
        widgets = {
            "origen": forms.TextInput(attrs={"class": "campo"}),
            "solicitante": forms.TextInput(attrs={"class": "campo"}),
            "territorio": forms.TextInput(attrs={"class": "campo"}),
            "responsable": forms.Select(attrs={"class": "campo"}),
            "unidad": forms.Select(attrs={"class": "campo"}),
            "area_apoyo": forms.TextInput(attrs={"class": "campo"}),
            "fecha_comprometida": forms.DateInput(attrs={"class": "campo", "type": "date"}),
            "estado": forms.TextInput(attrs={"class": "campo"}),
            "observaciones": forms.Textarea(attrs={"class": "campo", "rows": 3}),
        }
