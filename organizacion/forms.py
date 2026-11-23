from django import forms

from .models import Cargo, Persona, Unidad


class UnidadForm(forms.ModelForm):
    class Meta:
        model = Unidad
        fields = ["nombre", "ambito", "responsable", "estado"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "campo"}),
            "ambito": forms.TextInput(attrs={"class": "campo"}),
            "responsable": forms.TextInput(attrs={"class": "campo"}),
            "estado": forms.TextInput(attrs={"class": "campo"}),
        }


class CargoForm(forms.ModelForm):
    funciones_texto = forms.CharField(
        required=False,
        label="Funciones (una por línea)",
        widget=forms.Textarea(attrs={"class": "campo", "rows": 4}),
        help_text="Escribe cada función en una línea.",
    )

    class Meta:
        model = Cargo
        fields = ["nombre"]
        widgets = {"nombre": forms.TextInput(attrs={"class": "campo"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.funciones:
            self.fields["funciones_texto"].initial = "\n".join(self.instance.funciones)

    def save(self, commit=True):
        cargo = super().save(commit=False)
        texto = self.cleaned_data.get("funciones_texto") or ""
        cargo.funciones = [line.strip() for line in texto.splitlines() if line.strip()]
        if commit:
            cargo.save()
        return cargo


class PersonaForm(forms.ModelForm):
    roles_texto = forms.CharField(
        required=False,
        label="Roles (separados por coma)",
        widget=forms.TextInput(attrs={"class": "campo"}),
    )

    class Meta:
        model = Persona
        fields = ["nombre", "cargo", "delegacion", "estado"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "campo"}),
            "cargo": forms.Select(attrs={"class": "campo"}),
            "delegacion": forms.Select(attrs={"class": "campo"}),
            "estado": forms.TextInput(attrs={"class": "campo"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.roles:
            self.fields["roles_texto"].initial = ", ".join(self.instance.roles)

    def save(self, commit=True):
        persona = super().save(commit=False)
        texto = self.cleaned_data.get("roles_texto") or ""
        persona.roles = [r.strip() for r in texto.split(",") if r.strip()]
        if commit:
            persona.save()
        return persona
