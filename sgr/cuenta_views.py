"""Gestión de contraseñas en el sitio público (no en Django Admin).

- Cambiar la propia contraseña: cualquier usuario con sesión iniciada (/cuenta/clave/).
- Establecer o restablecer la contraseña de un funcionario: solo Acceso total (/cuenta/funcionarios/<id>/clave/),
  escribiéndola o generando una contraseña temporal (V4.2). En ambos casos la cuenta queda obligada a
  cambiarla al ingresar y la contraseña asignada vence tras SGR_CLAVE_TEMPORAL_HORAS.
- Recuperar la contraseña por correo con un enlace de un solo uso que vence (V4.2, /cuenta/recuperar/).
Todo usa los formularios de Django, que aplican AUTH_PASSWORD_VALIDATORS y guardan solo el hash.
La contraseña temporal se muestra una sola vez en la respuesta; nunca se registra en logs ni en mensajes.
"""
import logging

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables

from organizacion.models import Persona
from sgr import claves
from sgr.reglas import es_acceso_total

logger = logging.getLogger("sgr.auditoria")


class _Widgets:
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs.setdefault("class", "campo")
        return form


class CambiarClaveView(_Widgets, auth_views.PasswordChangeView):
    template_name = "registration/cambiar_clave.html"
    success_url = reverse_lazy("cambiar_clave_listo")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["obligatorio"] = claves.debe_cambiar(self.request.user)
        ctx["horas_temporal"] = claves.horas_temporal()
        return ctx

    def form_valid(self, form):
        # PasswordChangeView guarda el hash y llama a update_session_auth_hash: esta sesión sigue
        # activa y las demás sesiones de la cuenta quedan invalidadas.
        respuesta = super().form_valid(form)
        obligatorio = claves.debe_cambiar(self.request.user)
        claves.limpiar_cambio_obligatorio(self.request.user)
        logger.info("Usuario %s cambió su contraseña%s", self.request.user.get_username(), " (cambio obligatorio cumplido)" if obligatorio else "")
        return respuesta


class CambiarClaveListoView(auth_views.PasswordChangeDoneView):
    template_name = "registration/cambiar_clave_listo.html"


def _contexto_establecer(persona, usuario, detalle, form):
    return {"form": form, "persona": persona, "cuenta": usuario, "volver_url": detalle,
            "inicial": not usuario.has_usable_password(), "horas_temporal": claves.horas_temporal(),
            "puede_enviar": claves.puede_enviar_claves() and bool(usuario.email)}


@sensitive_variables("clave")
def _enviar_clave_temporal(usuario, clave, vence):
    asunto = "SGR: contraseña temporal"
    cuerpo = (f"Hola {usuario.get_full_name() or usuario.get_username()}:\n\n"
              f"Se generó una contraseña temporal para su cuenta «{usuario.get_username()}» del SGR.\n\n"
              f"Contraseña temporal: {clave}\n\n"
              f"Vence el {timezone.localtime(vence):%d-%m-%Y %H:%M}. Al ingresar, el sistema le pedirá cambiarla.\n"
              "Si usted no esperaba este correo, avise a un usuario con Acceso total.\n")
    send_mail(asunto, cuerpo, None, [usuario.email])


@sensitive_post_parameters("new_password1", "new_password2")
@sensitive_variables("clave")
@never_cache
def establecer_clave(request, persona_id):
    if not es_acceso_total(request.user):
        raise PermissionDenied("Solo Acceso total puede establecer contraseñas.")
    persona = get_object_or_404(Persona.objects.select_related("usuario"), pk=persona_id)
    detalle = reverse("catalog_detalle", args=["funcionarios", persona.pk])
    usuario = persona.usuario
    if usuario is None:
        messages.error(request, "Este funcionario no tiene una cuenta de usuario vinculada.")
        return redirect(detalle)
    if usuario.pk == request.user.pk:
        messages.info(request, "Para su propia cuenta use «Cambiar contraseña», que pide la contraseña actual.")
        return redirect("cambiar_clave")
    if (usuario.is_superuser or usuario.is_staff) and not request.user.is_superuser:
        raise PermissionDenied("Solo un superusuario puede restablecer la contraseña de una cuenta administrativa.")

    if request.method == "POST" and request.POST.get("accion") == "temporal":
        inicial = not usuario.has_usable_password()
        clave = claves.generar_clave_temporal(usuario)
        usuario.set_password(clave)
        usuario.save(update_fields=["password"])
        estado = claves.marcar_cambio_obligatorio(usuario, "temporal")
        enviado, error_envio = False, False
        if request.POST.get("enviar_correo") and claves.puede_enviar_claves() and usuario.email:
            try:
                _enviar_clave_temporal(usuario, clave, estado.vence_en)
                enviado = True
            except Exception as exc:  # no se registra el contenido del correo
                error_envio = True
                logger.warning("No se pudo enviar el correo de contraseña temporal a la cuenta %s (%s)", usuario.get_username(), type(exc).__name__)
        logger.info("%s generó una contraseña temporal %s para el usuario %s (vence %s; correo %s)", request.user.get_username(), "inicial" if inicial else "de restablecimiento", usuario.get_username(), estado.vence_en.isoformat(timespec="minutes"), "enviado" if enviado else "no enviado")
        respuesta = render(request, "registration/clave_temporal.html", {"persona": persona, "cuenta": usuario, "clave": clave, "vence": estado.vence_en, "enviado": enviado, "error_envio": error_envio, "volver_url": detalle, "horas_temporal": claves.horas_temporal()})
        respuesta["Pragma"] = "no-cache"
        return respuesta

    form = SetPasswordForm(usuario, request.POST or None)
    for field in form.fields.values():
        field.widget.attrs.setdefault("class", "campo")
    if request.method == "POST" and form.is_valid():
        inicial = not usuario.has_usable_password()
        form.save()
        claves.marcar_cambio_obligatorio(usuario, "restablecida")
        logger.info("%s estableció la contraseña %s del usuario %s", request.user.get_username(), "inicial" if inicial else "restablecida", usuario.get_username())
        messages.success(request, f"Contraseña {'inicial establecida' if inicial else 'restablecida'} para «{usuario.get_username()}». El sistema no la muestra ni la envía: comuníquela por un medio seguro. Al ingresar se le pedirá cambiarla, y deja de servir después de {claves.horas_temporal()} horas.")
        if not usuario.is_active:
            messages.warning(request, "La cuenta está desactivada: no podrá iniciar sesión hasta que se active.")
        return redirect(detalle)
    return render(request, "registration/establecer_clave.html", _contexto_establecer(persona, usuario, detalle, form))


# ---------- Recuperación por correo (V4.2)
class _FormRecuperar(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "Correo electrónico"
        self.fields["email"].widget.attrs.update({"class": "campo", "autocomplete": "email"})


class _Habilitada:
    def dispatch(self, request, *args, **kwargs):
        if not claves.recuperacion_habilitada():
            return render(request, "registration/recuperar_no_disponible.html", status=503)
        return super().dispatch(request, *args, **kwargs)


def _url_publica():
    """Dominio y esquema del enlace: SGR_URL_PUBLICA (p. ej. https://sgr.ejemplo.cl) o el host de la petición."""
    from urllib.parse import urlsplit
    url = getattr(settings, "SGR_URL_PUBLICA", "")
    if url:
        partes = urlsplit(url)
        return partes.netloc, partes.scheme == "https"
    return None, None


class RecuperarClaveView(_Habilitada, auth_views.PasswordResetView):
    template_name = "registration/recuperar.html"
    email_template_name = "registration/recuperar_correo.txt"
    subject_template_name = "registration/recuperar_asunto.txt"
    form_class = _FormRecuperar
    success_url = reverse_lazy("recuperar_enviado")

    def form_valid(self, form):
        ip = claves.ip_cliente(self.request)
        correo = form.cleaned_data["email"].strip().lower()
        if claves.excede_limite("ip", ip):
            logger.warning("Recuperación de contraseña limitada por IP")
            ctx = self.get_context_data(form=form)
            ctx["limitado"] = True
            return render(self.request, self.template_name, ctx, status=429)
        if claves.excede_limite("correo", correo):
            # Respuesta genérica: no se revela si el correo existe ni si se alcanzó el límite.
            logger.warning("Recuperación de contraseña limitada por correo")
            return redirect(self.success_url)
        dominio, https = _url_publica()
        form.save(
            domain_override=dominio,
            use_https=https if https is not None else self.request.is_secure(),
            token_generator=self.token_generator,
            from_email=self.from_email,
            email_template_name=self.email_template_name,
            subject_template_name=self.subject_template_name,
            request=self.request,
            extra_email_context={"horas_enlace": max(1, round(settings.PASSWORD_RESET_TIMEOUT / 3600)), "minutos_enlace": settings.PASSWORD_RESET_TIMEOUT // 60},
        )
        logger.info("Solicitud de recuperación de contraseña procesada (respuesta genérica)")
        return redirect(self.success_url)


class RecuperarEnviadoView(_Habilitada, auth_views.PasswordResetDoneView):
    template_name = "registration/recuperar_enviado.html"


@method_decorator(sensitive_post_parameters("new_password1", "new_password2"), name="dispatch")
class RecuperarConfirmarView(_Habilitada, auth_views.PasswordResetConfirmView):
    template_name = "registration/recuperar_confirmar.html"
    success_url = reverse_lazy("recuperar_listo")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if form is not None:
            for field in form.fields.values():
                field.widget.attrs.setdefault("class", "campo")
        return form

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        claves.limpiar_cambio_obligatorio(form.user)
        logger.info("Usuario %s restableció su contraseña con un enlace de recuperación", form.user.get_username())
        return respuesta


class RecuperarListoView(_Habilitada, auth_views.PasswordResetCompleteView):
    template_name = "registration/recuperar_listo.html"
