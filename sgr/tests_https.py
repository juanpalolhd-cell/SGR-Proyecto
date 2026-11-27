"""Pruebas HTTPS (V4.2): configuración segura controlada por variables de entorno.

Se carga sgr/settings.py con un entorno simulado (sin tocar el entorno real) y se prueba el
comportamiento con las opciones seguras activas, como quedaría detrás de nginx con TLS.
Cuentas y contraseñas sintéticas, solo en la base de pruebas aislada.
"""
import importlib.util
import os
import re
from pathlib import Path
from unittest import mock

from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse

from sgr.tests_v41 import BaseV41, CLAVE

SETTINGS = Path(__file__).resolve().parent / "settings.py"


def cargar(env):
    base = {k: v for k, v in os.environ.items() if not (k.startswith("DJANGO_") or k.startswith("SGR_") or k.startswith("DB_"))}
    base.update(env)
    with mock.patch.dict(os.environ, base, clear=True):
        spec = importlib.util.spec_from_file_location("sgr_settings_prueba_https", SETTINGS)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod


class ConfiguracionHttpsTests(SimpleTestCase):
    def test_desarrollo_sin_variables_sigue_en_http(self):
        s = cargar({})
        self.assertTrue(s.DEBUG)
        self.assertFalse(hasattr(s, "SECURE_PROXY_SSL_HEADER"))
        self.assertFalse(s.SESSION_COOKIE_SECURE)
        self.assertFalse(s.CSRF_COOKIE_SECURE)
        self.assertFalse(s.SECURE_SSL_REDIRECT)
        self.assertEqual(s.SECURE_HSTS_SECONDS, 0)

    def test_produccion_activa_cookies_seguras_y_proxy(self):
        s = cargar({"DJANGO_DEBUG": "False", "DJANGO_SECRET_KEY": "solo-para-pruebas-" + "x" * 40})
        self.assertEqual(s.SECURE_PROXY_SSL_HEADER, ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertTrue(s.SESSION_COOKIE_SECURE)
        self.assertTrue(s.CSRF_COOKIE_SECURE)
        self.assertFalse(s.SECURE_SSL_REDIRECT)  # nginx ya redirige 80 → 443

    def test_variables_del_kit_https(self):
        s = cargar({
            "DJANGO_DEBUG": "False", "DJANGO_SECRET_KEY": "solo-para-pruebas-" + "x" * 40,
            "DJANGO_ALLOWED_HOSTS": "44-213-253-178.sslip.io,44.213.253.178",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://44-213-253-178.sslip.io",
            "DJANGO_SECURE_SSL_REDIRECT": "True", "DJANGO_SECURE_HSTS_SECONDS": "3600",
            "SGR_URL_PUBLICA": "https://44-213-253-178.sslip.io",
        })
        self.assertIn("44-213-253-178.sslip.io", s.ALLOWED_HOSTS)
        self.assertEqual(s.CSRF_TRUSTED_ORIGINS, ["https://44-213-253-178.sslip.io"])
        self.assertTrue(s.SECURE_SSL_REDIRECT)
        self.assertEqual(s.SECURE_HSTS_SECONDS, 3600)
        self.assertFalse(s.SECURE_HSTS_INCLUDE_SUBDOMAINS)
        self.assertFalse(s.SECURE_HSTS_PRELOAD)
        self.assertTrue(s.SGR_URL_PUBLICA.startswith("https://"))

    def test_se_puede_desactivar_en_produccion(self):
        s = cargar({"DJANGO_DEBUG": "False", "DJANGO_SECRET_KEY": "solo-para-pruebas-" + "x" * 40,
                    "DJANGO_SECURE_COOKIES": "False", "DJANGO_SECURE_PROXY_SSL_HEADER": "False"})
        self.assertFalse(s.SESSION_COOKIE_SECURE)
        self.assertFalse(hasattr(s, "SECURE_PROXY_SSL_HEADER"))


SEGURO = dict(
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"), SECURE_SSL_REDIRECT=True,
    SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True, SECURE_HSTS_SECONDS=3600,
    ALLOWED_HOSTS=["sgr.prueba.invalid"], CSRF_TRUSTED_ORIGINS=["https://sgr.prueba.invalid"],
)
HTTPS = {"HTTP_X_FORWARDED_PROTO": "https", "HTTP_HOST": "sgr.prueba.invalid"}


@override_settings(**SEGURO)
class ComportamientoHttpsTests(BaseV41):
    def test_http_redirige_a_https(self):
        r = Client().get("/login/", HTTP_HOST="sgr.prueba.invalid")
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r["Location"], "https://sgr.prueba.invalid/login/")

    def test_https_por_proxy_entrega_login_con_hsts_y_cookie_segura(self):
        r = Client().get("/login/", **HTTPS)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Strict-Transport-Security"], "max-age=3600")
        self.assertTrue(r.cookies["csrftoken"]["secure"])

    def test_post_con_csrf_por_https_inicia_sesion_con_cookie_segura(self):
        c = Client(enforce_csrf_checks=True)
        r = c.get("/login/", **HTTPS)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.content.decode()).group(1)
        r = c.post("/login/", {"username": self.users["total"].username, "password": CLAVE, "csrfmiddlewaretoken": token},
                   HTTP_REFERER="https://sgr.prueba.invalid/login/", **HTTPS)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.cookies["sessionid"]["secure"])

    def test_post_sin_csrf_se_rechaza(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post("/login/", {"username": "x", "password": "y"}, HTTP_REFERER="https://sgr.prueba.invalid/login/", **HTTPS)
        self.assertEqual(r.status_code, 403)

    def test_origen_no_confiable_se_rechaza(self):
        c = Client(enforce_csrf_checks=True)
        r = c.get("/login/", **HTTPS)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.content.decode()).group(1)
        r = c.post("/login/", {"username": "x", "password": "y", "csrfmiddlewaretoken": token},
                   HTTP_REFERER="https://otro-sitio.invalid/", HTTP_ORIGIN="https://otro-sitio.invalid", **HTTPS)
        self.assertEqual(r.status_code, 403)

    def test_admin_por_https(self):
        r = Client().get("/admin/login/", **HTTPS)
        self.assertEqual(r.status_code, 200)

    def test_enlace_de_recuperacion_usa_https(self):
        from django.core import mail
        from django.core.cache import cache
        cache.clear()
        u = self.users["minimo"]; u.email = "minimo@example.invalid"; u.save()
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", SGR_URL_PUBLICA="https://sgr.prueba.invalid"):
            r = Client().post(reverse("recuperar_clave"), {"email": u.email}, **HTTPS)
            self.assertEqual(r.status_code, 302)
            self.assertIn("https://sgr.prueba.invalid/cuenta/recuperar/", mail.outbox[-1].body)
