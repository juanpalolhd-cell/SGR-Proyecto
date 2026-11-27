"""Autenticación que rechaza contraseñas asignadas (temporal o restablecida) ya vencidas."""
import logging

from django.contrib.auth.backends import ModelBackend

from sgr.claves import clave_vencida

logger = logging.getLogger("sgr.auditoria")


class ClaveTemporalBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user is not None and clave_vencida(user):
            if request is not None:
                request.sgr_clave_vencida = True
            logger.info("Inicio de sesión rechazado: contraseña asignada vencida (usuario %s)", user.get_username())
            return None
        return user
