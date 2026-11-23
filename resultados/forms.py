from django import forms

from .models import Meta, Periodo


class PeriodoForm(forms.ModelForm):
    class Meta:
        model = Periodo
        fields = ["nombre", "inicio", "termino", "dias_computables", "estado"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "campo"}),
            "inicio": forms.DateInput(attrs={"class": "campo", "type": "date"}),
            "termino": forms.DateInput(attrs={"class": "campo", "type": "date"}),
            "dias_computables": forms.NumberInput(attrs={"class": "campo"}),
            "estado": forms.TextInput(attrs={"class": "campo"}),
        }


class MetaForm(forms.ModelForm):
    class Meta:
        model = Meta
        fields = ["periodo", "persona", "item", "unidad", "meta", "avance", "ponderador"]
        widgets = {
            "periodo": forms.Select(attrs={"class": "campo"}),
            "persona": forms.Select(attrs={"class": "campo"}),
            "item": forms.TextInput(attrs={"class": "campo"}),
            "unidad": forms.TextInput(attrs={"class": "campo"}),
            "meta": forms.NumberInput(attrs={"class": "campo", "step": "0.01"}),
            "avance": forms.NumberInput(attrs={"class": "campo", "step": "0.01"}),
            "ponderador": forms.NumberInput(attrs={"class": "campo", "step": "0.01"}),
        }
