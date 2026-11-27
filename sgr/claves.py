"""Contraseñas temporales, cambio obligatorio y correo (V4.2).

Reglas de seguridad:
- La contraseña temporal se genera con ``secrets`` y cumple AUTH_PASSWORD_VALIDATORS.
- Solo se guarda su hash (``set_password``). Se muestra UNA vez en la página de confirmación;
  nunca se escribe en logs, mensajes (``django.contrib.messages``) ni en la base de datos.
- Solo se envía por correo si el backend es SMTP real (o ``locmem`` en pruebas): los backends
  ``console`` y ``filebased`` escribirían el secreto en la consola o en disco.
"""
import hashlib
import logging
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import password_validation
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

logger = logging.getLogger("sgr.auditoria")

# Sin caracteres ambiguos (0/O, 1/l/I) para dictarla o copiarla sin errores.
_MINUS = "abcdefghijkmnopqrstuvwxyz"
_MAYUS = "ABCDEFGHJKLMNPQRSTUVWXYZ"
_DIGITOS = "23456789"
_SIMBOLOS = "!#%*+-=?@"
LARGO_TEMPORAL = 16


def horas_temporal():
    return int(getattr(settings, "SGR_CLAVE_TEMPORAL_HORAS", 72))


@sensitive_variables("clave")
def generar_clave_temporal(usuario, largo=LARGO_TEMPORAL):
    """Devuelve una contraseña aleatoria que cumple los validadores configurados."""
    todos = _MINUS + _MAYUS + _DIGITOS + _SIMBOLOS
    for _ in range(50):
        partes = [secrets.choice(_MINUS), secrets.choice(_MAYUS), secrets.choice(_DIGITOS), secrets.choice(_SIMBOLOS)]
        partes += [secrets.choice(todos) for _ in range(largo - len(partes))]
        secrets.SystemRandom().shuffle(partes)
        clave = "".join(partes)
        try:
            password_validation.validate_password(clave, usuario)
        except ValidationError:
            continue
        return clave
    raise RuntimeError("No se pudo generar una contraseña temporal que cumpla los validadores.")


def estado_de(usuario):
    from organizacion.models import EstadoClave
    if not getattr(usuario, "pk", None):
        return None
    return EstadoClave.objects.filter(usuario_id=usuario.pk).first()


def marcar_cambio_obligatorio(usuario, motivo):
    """Exige cambiar la contraseña en el próximo uso y fija su vencimiento."""
    from organizacion.models import EstadoClave
    ahora = timezone.now()
    estado, _ = EstadoClave.objects.update_or_create(
        usuario=usuario,
        defaults={"debe_cambiar_clave": True, "marcado_en": ahora, "motivo": motivo, "vence_en": ahora + timedelta(hours=horas_temporal())},
    )
    return estado


def limpiar_cambio_obligatorio(usuario):
    from organizacion.models import EstadoClave
    EstadoClave.objects.filter(usuario_id=usuario.pk).update(debe_cambiar_clave=False, vence_en=None, cambiada_en=timezone.now())


def debe_cambiar(usuario):
    estado = estado_de(usuario)
    return bool(estado and estado.debe_cambiar_clave)


def clave_vencida(usuario):
    estado = estado_de(usuario)
    return bool(estado and estado.vencida())


# ---------- Correo
def _backend():
    return getattr(settings, "EMAIL_BACKEND", "")


def recuperacion_habilitada():
    """La recuperación por correo se ofrece si hay un backend que entregue mensajes."""
    return not _backend().endswith("dummy.EmailBackend")


def puede_enviar_claves():
    """Solo SMTP real (con servidor configurado) o locmem (pruebas) pueden llevar una contraseña."""
    b = _backend()
    if b.endswith("locmem.EmailBackend"):
        return True
    return b.endswith("smtp.EmailBackend") and bool(getattr(settings, "EMAIL_HOST", ""))


# ---------- Límite de solicitudes (caché compartida)
def ip_cliente(request):
    cabecera = getattr(settings, "SGR_PROXY_IP_HEADER", "")
    if cabecera:
        valor = request.META.get(cabecera, "")
        if valor:
            # X-Forwarded-For: el último salto lo agrega nginx y es el confiable.
            return valor.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "desconocida")


def excede_limite(tipo, valor, limite=None, ventana=None):
    limite = limite or int(getattr(settings, "SGR_RECUPERACION_LIMITE", 5))
    ventana = ventana or int(getattr(settings, "SGR_RECUPERACION_VENTANA", 3600))
    huella = hashlib.sha256(f"{tipo}:{valor}".encode()).hexdigest()[:32]
    clave = f"sgr:recuperar:{tipo}:{huella}"
    cache.add(clave, 0, ventana)
    try:
        n = cache.incr(clave)
    except ValueError:
        cache.set(clave, 1, ventana)
        n = 1
    return n > limite
