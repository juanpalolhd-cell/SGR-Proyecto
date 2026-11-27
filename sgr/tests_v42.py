"""Pruebas V4.2: contraseña temporal, cambio obligatorio y recuperación por correo.

Cuentas y contraseñas sintéticas, solo en la base de pruebas aislada. El correo usa locmem.
"""
import re
from datetime import timedelta
from unittest import mock

from django.contrib.auth import password_validation
from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.messages import get_messages
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from organizacion.models import EstadoClave, Persona
from sgr import claves
from sgr.tests_v41 import BaseV41, CLAVE, VALIDADORES

NUEVA = "MiClavePropia2026!x"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class BaseV42(BaseV41):
    def setUp(self):
        cache.clear()
        mail.outbox = []

    def crear_funcionario(self, correo="nueva@example.invalid"):
        self.login("total")
        base = self.rows[1]["funcionarios"]
        data = {"usuario": "", "nuevo_usuario": "cuenta_v42", "nombres": "Nueva", "apellidos": "Ficticia", "rut": "95004242-0", "correo": correo, "cargo": base.cargo_id, "delegacion": base.delegacion_id, "estado": "Activo"}
        self.client.post(reverse("catalog_crear", args=["funcionarios"]), data)
        return Persona.objects.get(usuario__username="cuenta_v42")

    def generar(self, persona, **extra):
        self.login("total")
        datos = {"accion": "temporal"}
        datos.update(extra)
        return self.client.post(reverse("establecer_clave", args=[persona.pk]), datos)


class ClaveTemporalTests(BaseV42):
    def test_se_ofrece_al_crear_y_se_muestra_una_sola_vez(self):
        persona = self.crear_funcionario()
        detalle = self.client.get(reverse("catalog_detalle", args=["funcionarios", persona.pk]) + "?nueva_cuenta=1")
        self.assertContains(detalle, "Generar contraseña temporal")
        with self.assertLogs("sgr.auditoria", level="INFO") as logs:
            r = self.generar(persona)
        clave = r.context["clave"]
        self.assertEqual(len(clave), claves.LARGO_TEMPORAL)
        self.assertContains(r, clave)
        self.assertContains(r, "única vez")
        self.assertIn("no-cache", r["Cache-Control"])
        self.assertIn("no-store", r["Cache-Control"])
        self.assertFalse(any(clave in str(m) for m in get_messages(r.wsgi_request)))
        self.assertFalse(any(clave in linea for linea in logs.output))
        usuario = User.objects.get(pk=persona.usuario_id)
        self.assertNotEqual(usuario.password, clave)
        self.assertTrue(usuario.password.startswith("pbkdf2_") or "$" in usuario.password)
        self.assertTrue(usuario.check_password(clave))
        self.assertNotIn(clave, str(list(EstadoClave.objects.values())))
        estado = EstadoClave.objects.get(usuario=usuario)
        self.assertTrue(estado.debe_cambiar_clave)
        self.assertEqual(estado.motivo, "temporal")
        self.assertAlmostEqual((estado.vence_en - timezone.now()).total_seconds() / 3600, 72, delta=0.1)
        # No vuelve a aparecer en ninguna otra pantalla.
        self.assertNotContains(self.client.get(reverse("catalog_detalle", args=["funcionarios", persona.pk])), clave)
        self.assertNotContains(self.client.get(reverse("establecer_clave", args=[persona.pk])), clave)

    @override_settings(AUTH_PASSWORD_VALIDATORS=VALIDADORES)
    def test_cumple_validadores_y_es_aleatoria(self):
        usuario = User.objects.create_user(username="validador_v42", email="v@example.invalid")
        generadas = {claves.generar_clave_temporal(usuario) for _ in range(30)}
        self.assertEqual(len(generadas), 30)
        for c in generadas:
            password_validation.validate_password(c, usuario)
            self.assertTrue(re.search(r"[a-z]", c) and re.search(r"[A-Z]", c) and re.search(r"[0-9]", c) and re.search(r"[!#%*+\-=?@]", c))

    def test_correo_opcional_solo_con_backend_seguro(self):
        persona = self.crear_funcionario()
        r = self.client.get(reverse("establecer_clave", args=[persona.pk]))
        self.assertContains(r, "Enviarla también por correo")
        r = self.generar(persona)
        self.assertEqual(len(mail.outbox), 0)
        r = self.generar(persona, enviar_correo="1")
        self.assertTrue(r.context["enviado"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["nueva@example.invalid"])
        self.assertIn(r.context["clave"], mail.outbox[0].body)
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"):
            self.assertNotContains(self.client.get(reverse("establecer_clave", args=[persona.pk])), "Enviarla también por correo")
            r = self.generar(persona, enviar_correo="1")
            self.assertFalse(r.context["enviado"])
        self.assertEqual(len(mail.outbox), 1)

    def test_solo_acceso_total(self):
        persona = self.crear_funcionario()
        for role in ("intermedio", "minimo"):
            self.login(role)
            r = self.client.post(reverse("establecer_clave", args=[persona.pk]), {"accion": "temporal"})
            self.assertEqual(r.status_code, 403)
        self.assertFalse(User.objects.get(pk=persona.usuario_id).has_usable_password())

    def test_vencida_rechaza_login_con_mensaje(self):
        persona = self.crear_funcionario()
        clave = self.generar(persona).context["clave"]
        EstadoClave.objects.filter(usuario_id=persona.usuario_id).update(vence_en=timezone.now() - timedelta(minutes=1))
        r = Client().post(reverse("login"), {"username": "cuenta_v42", "password": clave})
        self.assertContains(r, "contraseña temporal venció", status_code=400)
        self.assertNotIn("_auth_user_id", r.wsgi_request.session)
        # Con una contraseña incorrecta el mensaje sigue siendo genérico (no revela el estado de la cuenta).
        r = Client().post(reverse("login"), {"username": "cuenta_v42", "password": "otra-cualquiera"})
        self.assertContains(r, "Usuario o contraseña incorrectos", status_code=400)
        self.assertFalse(Client().login(username="cuenta_v42", password=clave))

    @override_settings(SGR_CLAVE_TEMPORAL_HORAS=1)
    def test_vencimiento_configurable_y_sesion_abierta_se_cierra(self):
        persona = self.crear_funcionario()
        clave = self.generar(persona).context["clave"]
        estado = EstadoClave.objects.get(usuario_id=persona.usuario_id)
        self.assertAlmostEqual((estado.vence_en - timezone.now()).total_seconds() / 3600, 1, delta=0.05)
        c = Client()
        c.post(reverse("login"), {"username": "cuenta_v42", "password": clave})
        with mock.patch("django.utils.timezone.now", return_value=timezone.now() + timedelta(hours=2)):
            r = c.get(reverse("cambiar_clave"))
        self.assertRedirects(r, reverse("login"), fetch_redirect_response=False)
        self.assertEqual(c.get("/gestion/").status_code, 302)
        self.assertIn("/login/", c.get("/gestion/")["Location"])


class CambioObligatorioTests(BaseV42):
    def entrar_con_temporal(self):
        persona = self.crear_funcionario()
        clave = self.generar(persona).context["clave"]
        c = Client()
        r = c.post(reverse("login"), {"username": "cuenta_v42", "password": clave})
        return persona, clave, c, r

    def test_redirige_hasta_cambiarla(self):
        persona, clave, c, r = self.entrar_con_temporal()
        self.assertRedirects(r, reverse("cambiar_clave"), fetch_redirect_response=False)
        for url in ("/", "/gestion/", "/agenda/", reverse("tablero_unidad"), "/admin/", reverse("recuperar_clave")):
            r = c.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertEqual(r["Location"], reverse("cambiar_clave"), url)
        r = c.get(reverse("cambiar_clave"))
        self.assertContains(r, "Cambio obligatorio")
        self.assertNotEqual(c.get("/static/css/style.css").get("Location"), reverse("cambiar_clave"))
        r = c.post(reverse("logout"))
        self.assertRedirects(r, reverse("login"), fetch_redirect_response=False)

    def test_cambio_limpia_bandera_e_invalida_otras_sesiones(self):
        persona, clave, c1, _ = self.entrar_con_temporal()
        c2 = Client()
        c2.post(reverse("login"), {"username": "cuenta_v42", "password": clave})
        self.assertEqual(c2.get("/gestion/")["Location"], reverse("cambiar_clave"))
        r = c1.post(reverse("cambiar_clave"), {"old_password": clave, "new_password1": NUEVA, "new_password2": NUEVA})
        self.assertRedirects(r, reverse("cambiar_clave_listo"))
        estado = EstadoClave.objects.get(usuario_id=persona.usuario_id)
        self.assertFalse(estado.debe_cambiar_clave)
        self.assertIsNone(estado.vence_en)
        self.assertIsNotNone(estado.cambiada_en)
        self.assertEqual(c1.get("/gestion/").status_code, 200)  # esta sesión sigue (update_session_auth_hash)
        r = c2.get("/gestion/")  # la otra sesión quedó invalidada
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])
        self.assertTrue(Client().login(username="cuenta_v42", password=NUEVA))
        self.assertFalse(Client().login(username="cuenta_v42", password=clave))

    def test_restablecer_escrita_tambien_obliga(self):
        persona = self.crear_funcionario()
        self.login("total")
        self.client.post(reverse("establecer_clave", args=[persona.pk]), {"new_password1": "EscritaPorTotal123!", "new_password2": "EscritaPorTotal123!"})
        estado = EstadoClave.objects.get(usuario_id=persona.usuario_id)
        self.assertTrue(estado.debe_cambiar_clave)
        self.assertEqual(estado.motivo, "restablecida")
        c = Client()
        r = c.post(reverse("login"), {"username": "cuenta_v42", "password": "EscritaPorTotal123!"})
        self.assertRedirects(r, reverse("cambiar_clave"), fetch_redirect_response=False)

    def test_cuentas_existentes_no_se_ven_afectadas(self):
        self.assertFalse(EstadoClave.objects.exists())
        c = Client()
        r = c.post(reverse("login"), {"username": "v41_minimo", "password": CLAVE})
        self.assertRedirects(r, reverse("home"), fetch_redirect_response=False)
        self.assertEqual(c.get("/gestion/").status_code, 200)
        self.assertTrue(User.objects.get(username="v41_minimo").check_password(CLAVE))

    def test_setup_roles_idempotente_sin_permisos_internos(self):
        call_command("setup_roles", verbosity=0)
        call_command("setup_roles", verbosity=0)
        conteos = {g.name: g.permissions.count() for g in Group.objects.filter(name__in=["Acceso total", "Intermedio", "Minimo"])}
        # V4.3: +Empresa (4 permisos; Intermedio y Mínimo solo ver), +Solicitud (4; Intermedio ver/crear/editar,
        # Mínimo ver) y +HistorialSolicitud (solo lectura para todos): 85+9, 38+5, 22+3.
        self.assertEqual(conteos, {"Acceso total": 94, "Intermedio": 43, "Minimo": 25})
        self.assertFalse(Permission.objects.filter(content_type__model="estadoclave", group__isnull=False).exists())


class RecuperacionCorreoTests(BaseV42):
    def setUp(self):
        super().setUp()
        self.usuario = User.objects.create_user(username="recupera_v42", email="recupera@example.invalid", password=CLAVE)

    def pedir(self, correo, ip="10.0.0.1", client=None):
        return (client or Client()).post(reverse("recuperar_clave"), {"email": correo}, REMOTE_ADDR=ip)

    def enlace(self):
        cuerpo = mail.outbox[-1].body
        return re.search(r"https?://[^/\s]+(/cuenta/recuperar/[^\s]+/)", cuerpo)

    def test_login_ofrece_recuperar(self):
        r = Client().get(reverse("login"))
        self.assertContains(r, reverse("recuperar_clave"))
        self.assertContains(r, "¿Olvidó su contraseña?")

    def test_flujo_completo_y_enlace_de_un_solo_uso(self):
        EstadoClave.objects.create(usuario=self.usuario, debe_cambiar_clave=True, motivo="temporal", vence_en=timezone.now() - timedelta(hours=1))
        r = self.pedir("RECUPERA@example.invalid")
        self.assertRedirects(r, reverse("recuperar_enviado"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["recupera@example.invalid"])
        self.assertIn("una sola vez", mail.outbox[0].body)
        ruta = self.enlace().group(1)
        c = Client()
        r = c.get(ruta)
        self.assertEqual(r.status_code, 302)  # Django oculta el token en la sesión
        r = c.get(r["Location"])
        self.assertContains(r, "Crear una contraseña nueva")
        r = c.post(r.wsgi_request.path, {"new_password1": NUEVA, "new_password2": NUEVA})
        self.assertRedirects(r, reverse("recuperar_listo"))
        self.assertTrue(Client().login(username="recupera_v42", password=NUEVA))
        self.assertFalse(EstadoClave.objects.get(usuario=self.usuario).debe_cambiar_clave)
        # Reutilizar el mismo enlace ya no sirve.
        r = Client().get(ruta, follow=True)
        self.assertContains(r, "Enlace no válido")
        self.assertFalse(r.context["validlink"])

    def test_enlace_vencido(self):
        uid = urlsafe_base64_encode(force_bytes(self.usuario.pk))
        token = default_token_generator.make_token(self.usuario)
        ruta = reverse("recuperar_confirmar", args=[uid, token])
        futuro = default_token_generator._now() + timedelta(seconds=3601)
        with mock.patch.object(type(default_token_generator), "_now", return_value=futuro):
            r = Client().get(ruta, follow=True)
        self.assertContains(r, "Enlace no válido")
        self.assertTrue(self.usuario.check_password(CLAVE))

    @override_settings(PASSWORD_RESET_TIMEOUT=120)
    def test_vencimiento_configurable(self):
        uid = urlsafe_base64_encode(force_bytes(self.usuario.pk))
        token = default_token_generator.make_token(self.usuario)
        futuro = default_token_generator._now() + timedelta(seconds=180)
        with mock.patch.object(type(default_token_generator), "_now", return_value=futuro):
            self.assertFalse(default_token_generator.check_token(self.usuario, token))
        self.pedir("recupera@example.invalid")
        self.assertIn("vence en 2 minutos", mail.outbox[0].body)

    def test_respuesta_generica(self):
        r1 = self.pedir("noexiste@example.invalid", ip="10.0.0.2")
        r2 = self.pedir("recupera@example.invalid", ip="10.0.0.3")
        self.assertEqual((r1.status_code, r1["Location"]), (r2.status_code, r2["Location"]))
        self.assertEqual(len(mail.outbox), 1)
        p1 = Client().get(r1["Location"])
        self.assertContains(p1, "exista o no la cuenta")
        # Cuentas inactivas tampoco reciben correo, con la misma respuesta.
        self.usuario.is_active = False
        self.usuario.save()
        r3 = self.pedir("recupera@example.invalid", ip="10.0.0.4")
        self.assertEqual(r3["Location"], r1["Location"])
        self.assertEqual(len(mail.outbox), 1)

    def test_limite_por_correo(self):
        for i in range(7):
            r = self.pedir("recupera@example.invalid", ip=f"10.1.0.{i}")
            self.assertRedirects(r, reverse("recuperar_enviado"))
        self.assertEqual(len(mail.outbox), 5)

    def test_limite_por_ip(self):
        for i in range(5):
            self.assertEqual(self.pedir(f"otro{i}@example.invalid", ip="10.2.0.9").status_code, 302)
        r = self.pedir("recupera@example.invalid", ip="10.2.0.9")
        self.assertContains(r, "Demasiadas solicitudes", status_code=429)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(self.pedir("recupera@example.invalid", ip="10.2.0.10").status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(SGR_URL_PUBLICA="https://sgr.ejemplo.cl")
    def test_enlace_con_dominio_publico(self):
        self.pedir("recupera@example.invalid")
        self.assertIn("https://sgr.ejemplo.cl/cuenta/recuperar/", mail.outbox[0].body)

    def test_enlace_con_host_de_la_peticion_por_defecto(self):
        self.pedir("recupera@example.invalid")
        self.assertIn("http://testserver/cuenta/recuperar/", mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.dummy.EmailBackend")
    def test_sin_correo_configurado_no_se_ofrece(self):
        self.assertContains(Client().get(reverse("login")), "no está habilitada")
        self.assertEqual(Client().get(reverse("recuperar_clave")).status_code, 503)

    @override_settings(SGR_PROXY_IP_HEADER="HTTP_X_FORWARDED_FOR")
    def test_ip_detras_de_nginx(self):
        req = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="1.2.3.4, 203.0.113.7", REMOTE_ADDR="127.0.0.1")
        self.assertEqual(claves.ip_cliente(req), "203.0.113.7")
        self.assertEqual(claves.ip_cliente(RequestFactory().get("/", REMOTE_ADDR="127.0.0.1")), "127.0.0.1")
