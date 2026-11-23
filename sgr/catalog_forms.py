"""Public ModelForms: never grant privileges or expose credentials."""
from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from organizacion.models import Unidad, Persona, Cargo, Rol, Territorio, Vecino, JuntaVecinos, Participacion, TipoAtencion, SubAtencion
from agenda.models import Hito
from actividades.models import Actividad, Evidencia, GestionSocial
from resultados.models import Periodo, Meta, CatalogoMeta

class BaseForm(forms.ModelForm):
    required_fields = ()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "campo")
            if isinstance(field, forms.DateField):
                field.widget = forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "campo"})
            if name == "codigo":
                field.help_text = "Único. Si lo deja vacío, se genera automáticamente."
        for name in self.required_fields:
            self.fields[name].required = True

class DelegacionForm(BaseForm):
    required_fields = ("direccion",)
    class Meta:
        model = Unidad
        fields = ["codigo", "nombre", "direccion", "delegado", "estado"]
    def clean(self):
        data = super().clean()
        delegado = data.get("delegado")
        if delegado and self.instance.pk and delegado.delegacion_id != self.instance.pk:
            self.add_error("delegado", "El delegado debe pertenecer a esta delegación.")
        return data

class CargoForm(BaseForm):
    required_fields = ("descripcion",)
    class Meta:
        model = Cargo
        fields = ["codigo", "nombre", "descripcion", "estado"]

class RolForm(BaseForm):
    class Meta:
        model = Rol
        fields = ["codigo", "nombre", "descripcion", "estado"]

class FuncionarioForm(BaseForm):
    nuevo_usuario = forms.CharField(max_length=150, required=False, help_text="Solo para crear una cuenta nueva sin acceso inicial. Su contraseña se establece por un administrador en el medio protegido; no se envía por correo.")
    required_fields = ("nombres", "apellidos", "rut", "correo")
    class Meta:
        model = Persona
        fields = ["usuario", "nuevo_usuario", "nombres", "apellidos", "rut", "correo", "cargo", "delegacion", "estado"]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = User.objects.filter(funcionario_sgr__isnull=True) | User.objects.filter(pk=self.instance.usuario_id)
        if self.instance.pk:
            self.fields["usuario"].disabled = True
            self.fields["nuevo_usuario"].disabled = True
    def clean(self):
        data = super().clean()
        username = data.get("nuevo_usuario", "").strip()
        if not data.get("usuario") and not username:
            self.add_error("usuario", "Seleccione una cuenta existente o indique un nuevo usuario.")
        if data.get("usuario") and username:
            self.add_error("nuevo_usuario", "Elija una cuenta existente o cree una nueva, no ambas.")
        if username:
            from django.contrib.auth.validators import UnicodeUsernameValidator
            try: UnicodeUsernameValidator()(username)
            except forms.ValidationError as exc: self.add_error("nuevo_usuario", exc)
            if User.objects.filter(username=username).exists():
                self.add_error("nuevo_usuario", "El nombre de usuario ya existe; seleccione la cuenta si corresponde.")
        return data
    @transaction.atomic
    def save(self, commit=True):
        obj = super().save(commit=False)
        if not obj.usuario_id:
            user = User(username=self.cleaned_data["nuevo_usuario"], first_name=obj.nombres, last_name=obj.apellidos, email=obj.correo, is_staff=False, is_superuser=False)
            user.set_unusable_password()
            user.save()
            obj.usuario = user
        if commit:
            obj.save()
            self.save_m2m()
        return obj

class TerritorioForm(BaseForm):
    required_fields = ("descripcion",)
    class Meta:
        model = Territorio
        fields = ["codigo", "nombre", "descripcion", "delegacion", "estado"]

class VecinoForm(BaseForm):
    class Meta:
        model = Vecino
        fields = ["rut", "nombres", "apellidos", "telefono", "correo", "direccion", "territorio", "estado"]

class JuntaForm(BaseForm):
    class Meta:
        model = JuntaVecinos
        fields = ["codigo", "nombre", "direccion", "delegacion", "territorio", "fecha_constitucion", "estado"]

class ParticipacionForm(BaseForm):
    class Meta:
        model = Participacion
        fields = ["vecino", "junta", "dirigente", "cargo", "fecha_incorporacion", "estado"]

class HitoForm(BaseForm):
    class Meta:
        model = Hito
        fields = ["codigo", "nombre", "descripcion", "periodicidad", "fecha_inicio", "fecha_termino", "delegacion", "territorio", "responsables", "estado"]
    def clean(self):
        data = super().clean()
        delegation, people = data.get("delegacion"), data.get("responsables")
        if delegation and people is not None and people.exclude(delegacion=delegation).exists():
            self.add_error("responsables", "Los responsables deben pertenecer a la delegación seleccionada.")
        return data

class ActividadForm(BaseForm):
    required_fields = ("asignacion", "origen", "solicitante", "territorio", "responsable", "fecha_compromiso", "apoyo")
    class Meta:
        model = Actividad
        fields = ["codigo", "fecha", "persona", "asignacion", "hito", "tipo", "descripcion", "origen", "solicitante", "unidad", "territorio", "responsable", "fecha_compromiso", "apoyo", "avance", "estado", "resultado"]
    def clean(self):
        data = super().clean()
        if data.get("responsable") and data.get("unidad") and data["responsable"].delegacion_id != data["unidad"].pk:
            self.add_error("responsable", "El responsable debe pertenecer a la delegación seleccionada.")
        return data

class TipoForm(BaseForm):
    required_fields = ("descripcion",)
    class Meta:
        model = TipoAtencion
        fields = ["codigo", "nombre", "descripcion", "estado"]

class SubtipoForm(BaseForm):
    class Meta:
        model = SubAtencion
        fields = ["codigo", "nombre", "tipo_atencion", "descripcion", "estado"]

class MetaForm(BaseForm):
    class Meta:
        model = CatalogoMeta
        fields = ["codigo", "nombre", "descripcion", "tipo", "unidad_medida", "requiere_evidencia", "estado"]

class AsignacionForm(BaseForm):
    required_fields = ("catalogo",)
    class Meta:
        model = Meta
        fields = ["persona", "catalogo", "periodo", "meta", "ponderador", "fecha_asignacion", "observacion", "estado"]
    def save(self, commit=True):
        obj = super().save(commit=False)
        if obj.catalogo_id:
            obj.item, obj.unidad = obj.catalogo.nombre, obj.catalogo.unidad_medida
        if commit: obj.save()
        return obj

class EvidenciaForm(BaseForm):
    required_fields = ("autor_usuario",)
    class Meta:
        model = Evidencia
        fields = ["codigo", "actividad", "gestion_social", "tipo", "ruta", "autor_usuario", "fecha", "estado", "observacion", "verificador_usuario"]
    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.autor = obj.autor_usuario.get_username() if obj.autor_usuario_id else ""
        obj.verificador = obj.verificador_usuario.get_username() if obj.verificador_usuario_id else ""
        if commit: obj.save()
        return obj

class TrimestreForm(BaseForm):
    class Meta:
        model = Periodo
        fields = ["codigo", "nombre", "anio", "numero", "inicio", "termino", "estado"]
    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.dias_computables = (obj.termino - obj.inicio).days + 1
        if commit: obj.save()
        return obj

class GestionForm(BaseForm):
    class Meta:
        model = GestionSocial
        fields = ["fecha_ingreso", "fecha_atencion", "beneficiario", "tipo", "subtipo", "asignacion", "visita", "actuaciones", "derivacion", "informe", "beneficio", "resultado", "estado"]
