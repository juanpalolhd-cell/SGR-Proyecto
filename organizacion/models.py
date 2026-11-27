from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError
from sgr.domain import DomainMixin
from sgr.reglas import validar_telefono


class Unidad(DomainMixin, models.Model):
    codigo = models.CharField(max_length=30, unique=True, null=True, blank=True)
    direccion = models.CharField(max_length=250, blank=True)
    delegado = models.ForeignKey("Persona", null=True, blank=True, on_delete=models.PROTECT, related_name="delegaciones_a_cargo")
    nombre = models.CharField(max_length=150)
    ambito = models.CharField(max_length=200)
    responsable = models.CharField(max_length=120)
    estado = models.CharField(max_length=50, default="Activa")

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Unidad"
        verbose_name_plural = "Unidades"

    def __str__(self):
        return self.nombre


class Cargo(DomainMixin, models.Model):
    codigo = models.CharField(max_length=30, unique=True, null=True, blank=True)
    descripcion = models.TextField(blank=True)
    estado = models.BooleanField(default=True)
    nombre = models.CharField(max_length=120, unique=True)
    funciones = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"

    def __str__(self):
        return self.nombre


class Persona(DomainMixin, models.Model):
    usuario = models.OneToOneField(User, null=True, blank=True, on_delete=models.PROTECT, related_name="funcionario_sgr")
    nombres = models.CharField(max_length=150, blank=True)
    apellidos = models.CharField(max_length=150, blank=True)
    rut = models.CharField("RUT ficticio", max_length=20, unique=True, null=True, blank=True)
    correo = models.EmailField(blank=True)
    roles_rel = models.ManyToManyField("Rol", blank=True, related_name="funcionarios")

    def save(self, *args, **kwargs):
        if self.nombres or self.apellidos:
            self.nombre = (self.nombres + " " + self.apellidos).strip()
        super().save(*args, **kwargs)

    nombre = models.CharField(max_length=150)
    cargo = models.ForeignKey("Cargo", on_delete=models.PROTECT, related_name="personas")
    delegacion = models.ForeignKey("Unidad", on_delete=models.PROTECT, related_name="personas")
    roles = models.JSONField(default=list, blank=True)
    estado = models.CharField(max_length=50, default="Activo")

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Persona"
        verbose_name_plural = "Personas"

    def __str__(self):
        return self.nombre


class Delegacion(DomainMixin, models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=150)
    estado = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Delegación"
        verbose_name_plural = "Delegaciones"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Rol(DomainMixin, models.Model):
    codigo = models.CharField(max_length=30, unique=True, null=True, blank=True)
    grupo = models.ForeignKey("auth.Group", null=True, blank=True, on_delete=models.PROTECT, related_name="roles_sgr")
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True)
    estado = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.nombre


class PerfilUsuario(DomainMixin, models.Model):
    usuario = models.OneToOneField(User, on_delete=models.PROTECT, related_name="perfil_usuario")
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name="perfiles")
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name="perfiles")
    estado = models.BooleanField(default=True)

    class Meta:
        ordering = ["usuario__username"]
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"

    def __str__(self):
        return f"{self.usuario.username} ({self.rol})"


class Item(DomainMixin, models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    estado = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Ítem"
        verbose_name_plural = "Ítems"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class TipoAtencion(DomainMixin, models.Model):
    descripcion = models.TextField(blank=True)
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=150)
    estado = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Tipo de atención"
        verbose_name_plural = "Tipos de atención"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class SubAtencion(DomainMixin, models.Model):
    tipo_atencion = models.ForeignKey(TipoAtencion, on_delete=models.PROTECT, related_name="subatenciones")
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    estado = models.BooleanField(default=True)

    class Meta:
        ordering = ["tipo_atencion", "nombre"]
        verbose_name = "Subatención"
        verbose_name_plural = "Subatenciones"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Territorio(DomainMixin, models.Model):
    codigo = models.CharField(max_length=30, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    delegacion = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="territorios")
    estado = models.BooleanField(default=True)
    def __str__(self): return self.nombre


class Vecino(DomainMixin, models.Model):
    rut = models.CharField("RUT ficticio", max_length=20, unique=True)
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150)
    telefono = models.CharField(max_length=30, validators=[validar_telefono])
    correo = models.EmailField()
    direccion = models.CharField(max_length=250)
    territorio = models.ForeignKey(Territorio, on_delete=models.PROTECT, related_name="vecinos")
    estado = models.BooleanField(default=True)
    def __str__(self): return f"{self.nombres} {self.apellidos}"


class JuntaVecinos(DomainMixin, models.Model):
    codigo = models.CharField(max_length=30, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=250)
    delegacion = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="juntas")
    territorio = models.ForeignKey(Territorio, on_delete=models.PROTECT, related_name="juntas")
    fecha_constitucion = models.DateField()
    estado = models.BooleanField(default=True)
    def __str__(self): return self.nombre


class Participacion(DomainMixin, models.Model):
    vecino = models.ForeignKey(Vecino, on_delete=models.PROTECT, related_name="participaciones")
    junta = models.ForeignKey(JuntaVecinos, on_delete=models.PROTECT, related_name="participaciones")
    dirigente = models.BooleanField(default=False)
    cargo = models.CharField(max_length=120, blank=True)
    fecha_incorporacion = models.DateField()
    estado = models.BooleanField(default=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["vecino", "junta"], name="participacion_vecino_junta_unica")]
    def __str__(self): return f"{self.vecino} — {self.junta}"
    def clean(self):
        super().clean()
        if self.vecino_id and self.junta_id and self.vecino.territorio_id != self.junta.territorio_id:
            raise ValidationError({"junta": "La junta debe pertenecer al territorio del vecino."})
        if self.dirigente and not self.cargo:
            raise ValidationError({"cargo": "Indique el cargo de dirigente."})


class EstadoClave(models.Model):
    """Estado de la contraseña de una cuenta (V4.2): cambio obligatorio y vencimiento de la clave temporal.

    No guarda contraseñas: solo banderas y fechas. Las cuentas sin registro no tienen restricciones.
    """
    MOTIVOS = [("temporal", "Contraseña temporal generada"), ("restablecida", "Contraseña establecida por Acceso total")]
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name="estado_clave")
    debe_cambiar_clave = models.BooleanField(default=False)
    marcado_en = models.DateTimeField(null=True, blank=True)
    motivo = models.CharField(max_length=20, choices=MOTIVOS, blank=True)
    vence_en = models.DateTimeField(null=True, blank=True, help_text="Después de esta fecha la contraseña asignada ya no permite iniciar sesión.")
    cambiada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Estado de contraseña"
        verbose_name_plural = "Estados de contraseña"

    def __str__(self):
        return f"{self.usuario.username}: {'debe cambiarla' if self.debe_cambiar_clave else 'al día'}"

    def vencida(self, ahora=None):
        from django.utils import timezone
        return bool(self.debe_cambiar_clave and self.vence_en and (ahora or timezone.now()) >= self.vence_en)


class Empresa(DomainMixin, models.Model):
    """V4.3: empresa o contratista a la que se deriva la ejecución de una solicitud."""
    codigo = models.CharField(max_length=30, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=150, unique=True)
    rut = models.CharField("RUT ficticio", max_length=20, unique=True, null=True, blank=True)
    rubro = models.CharField(max_length=150, blank=True)
    contacto = models.CharField(max_length=150, blank=True)
    telefono = models.CharField(max_length=30, blank=True, validators=[validar_telefono])
    correo = models.EmailField(blank=True)
    estado = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Empresa contratista"
        verbose_name_plural = "Empresas contratistas"

    def __str__(self):
        return self.nombre


def participaciones_vigentes(vecino):
    """Participaciones activas del vecino en juntas de vecinos (V4.3)."""
    if not vecino:
        return []
    return list(Participacion.objects.filter(vecino=vecino, estado=True).select_related("junta").order_by("-dirigente", "junta__nombre"))


def resumen_jjvv(vecino):
    """Texto y datos de pertenencia a JJVV y cargo para la consulta al ingresar una solicitud."""
    parts = participaciones_vigentes(vecino)
    if not parts:
        return {"pertenece": False, "con_cargo": False, "junta": None, "cargo": "", "texto": "No pertenece a ninguna junta de vecinos registrada · Sin cargo"}
    p = parts[0]
    cargo = p.cargo.strip() if p.dirigente and p.cargo else ""
    if cargo:
        texto = f"Pertenece a JJVV {p.junta.nombre} – cargo {cargo}"
    else:
        texto = f"Pertenece a JJVV {p.junta.nombre} – Sin cargo"
    if len(parts) > 1:
        texto += f" (y {len(parts) - 1} junta(s) más)"
    return {"pertenece": True, "con_cargo": bool(cargo), "junta": p.junta, "cargo": cargo, "texto": texto}
