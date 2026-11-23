from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError
from sgr.domain import DomainMixin


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
    telefono = models.CharField(max_length=30)
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
