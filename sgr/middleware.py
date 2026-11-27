"""Require authentication for public pages; leave /admin/, /login/ and static alone."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:
    """Redirect anonymous users to LOGIN_URL except for exempt prefixes."""

    def __init__(self, get_response):
        self.get_response = get_response
        raw = getattr(
            settings,
            'LOGIN_EXEMPT_URLS',
            ['/login/', '/logout/', '/admin/', '/static/'],
        )
        self.exempt = tuple(raw)

    def __call__(self, request):
        path = request.path
        if request.user.is_authenticated:
            return self.get_response(request)
        if any(path.startswith(prefix) for prefix in self.exempt):
            return self.get_response(request)
        return redirect(f"{settings.LOGIN_URL}?next={path}")


class CambioClaveObligatorioMiddleware:
    """V4.2: si la cuenta debe cambiar su contraseña, solo deja usar la página de cambio,
    el cierre de sesión y los archivos estáticos. Si la contraseña asignada venció, cierra la sesión."""

    LIBRES = ('/logout/', '/static/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and not request.path.startswith(self.LIBRES):
            from sgr.claves import estado_de
            estado = estado_de(user)
            if estado is not None and estado.debe_cambiar_clave:
                if estado.vencida():
                    logout(request)
                    messages.error(request, 'Su contraseña temporal venció. Pida una nueva a un usuario con Acceso total o use «¿Olvidó su contraseña?».')
                    return redirect(settings.LOGIN_URL)
                cambio = reverse('cambiar_clave')
                if not request.path.startswith(cambio):
                    return redirect(cambio)
        return self.get_response(request)
