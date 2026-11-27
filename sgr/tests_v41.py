"""Pruebas V4.1: tubo de trabajo, reglas del cliente y gestión de contraseñas.

Todas las cuentas y contraseñas son sintéticas y solo existen en la base de pruebas aislada.
"""
import contextlib
import io
from datetime import date, timedelta
from decimal import Decimal
from importlib import import_module
from unittest import mock

from django.apps import apps as django_apps
from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from actividades.models import Actividad, Evidencia, GestionSocial
from agenda.models import Compromiso, HistorialEstado
from organizacion.models import Persona, Vecino
from resultados.calculos import avance_calculado, meta_esperada
from resultados.models import Meta, Periodo
from sgr import catalog_forms as forms
from sgr.demo_data import create_demo

CLAVE = "SoloPruebaAislada123!"
VALIDADORES = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


class BaseV41(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rows = create_demo()
        call_command("setup_roles", verbosity=0)
        cls.users = {}
        for role, group in [("total", "Acceso total"), ("intermedio", "Intermedio"), ("minimo", "Minimo")]:
            u = User.objects.create_user(username="v41_" + role, password=CLAVE)
            u.groups.add(Group.objects.get(name=group))
            cls.users[role] = u

    def login(self, role):
        self.client.force_login(self.users[role])

    def compromiso(self, **extra):
        p = self.rows[1]["funcionarios"]
        datos = dict(origen="Solicitud", solicitante="Junta ficticia", territorio="Sector ficticio", responsable=p, unidad=p.delegacion, area_apoyo="Aseo", fecha_comprometida=timezone.localdate() + timedelta(days=30), estado="Ingresado")
        datos.update(extra)
        return Compromiso.objects.create(**datos)

    def post_compromiso(self, url, **cambios):
        p = self.rows[1]["funcionarios"]
        data = {"origen": "Solicitud", "solicitante": "Junta ficticia", "territorio": "Sector ficticio", "responsable": p.pk, "unidad": p.delegacion_id, "area_apoyo": "Aseo", "fecha_comprometida": (timezone.localdate() + timedelta(days=30)).isoformat(), "estado": "Ingresado", "observaciones": "", "observacion_cambio": ""}
        data.update(cambios)
        return self.client.post(url, data)


class TuboDeTrabajoTests(BaseV41):
    def test_menu_tiene_tubo_y_conserva_hitos(self):
        self.login("minimo")
        r = self.client.get("/gestion/")
        self.assertContains(r, 'href="/agenda/">Tubo de trabajo')
        self.assertContains(r, "/gestion/hitos/")

    def test_crear_registra_historial_con_usuario(self):
        self.login("intermedio")
        r = self.post_compromiso(reverse("crear_compromiso"))
        self.assertEqual(r.status_code, 302)
        c = Compromiso.objects.latest("pk")
        h = c.historial.get()
        self.assertEqual((h.estado_anterior, h.estado_nuevo, h.usuario), ("", "Ingresado", self.users["intermedio"]))

    def test_nuevo_no_puede_nacer_realizado(self):
        self.login("intermedio")
        antes = Compromiso.objects.count()
        r = self.post_compromiso(reverse("crear_compromiso"), estado="Realizado")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Compromiso.objects.count(), antes)
        c = Compromiso(responsable=self.rows[1]["funcionarios"], unidad=self.rows[1]["funcionarios"].delegacion, origen="a", solicitante="b", territorio="c", area_apoyo="d", fecha_comprometida=date(2026, 1, 1), estado="Realizado")
        with self.assertRaises(ValidationError):
            c.full_clean()

    def test_transiciones_validadas_en_clean(self):
        c = self.compromiso()
        c.estado = "Realizado"
        with self.assertRaises(ValidationError) as ctx:
            c.full_clean()
        self.assertIn("Transición no permitida", str(ctx.exception))
        c.estado = "Pendiente"
        c.full_clean()

    def test_editar_cambia_estado_y_guarda_de_a(self):
        c = self.compromiso()
        self.login("intermedio")
        r = self.post_compromiso(reverse("editar_compromiso", args=[c.pk]), estado="Pendiente", observacion_cambio="Se espera cuadrilla")
        self.assertEqual(r.status_code, 302)
        h = c.historial.get()
        self.assertEqual((h.estado_anterior, h.estado_nuevo, h.observacion, h.usuario), ("Ingresado", "Pendiente", "Se espera cuadrilla", self.users["intermedio"]))
        r = self.post_compromiso(reverse("editar_compromiso", args=[c.pk]), estado="Realizado")
        self.assertEqual(r.status_code, 302)
        detalle = self.client.get(reverse("detalle_compromiso", args=[c.pk]))
        self.assertContains(detalle, "Historial de estados")
        self.assertContains(detalle, "Se espera cuadrilla")

    def test_salto_no_permitido_por_formulario(self):
        c = self.compromiso()
        self.login("intermedio")
        r = self.post_compromiso(reverse("editar_compromiso", args=[c.pk]), estado="Realizado")
        self.assertEqual(r.status_code, 200)
        c.refresh_from_db()
        self.assertEqual(c.estado, "Ingresado")

    def test_reabrir_realizado_exige_observacion(self):
        c = self.compromiso(estado="Realizado")
        self.login("intermedio")
        r = self.post_compromiso(reverse("editar_compromiso", args=[c.pk]), estado="En proceso")
        self.assertEqual(r.status_code, 200)
        r = self.post_compromiso(reverse("editar_compromiso", args=[c.pk]), estado="En proceso", observacion_cambio="Vecinos reportan que falta")
        self.assertEqual(r.status_code, 302)
        c.refresh_from_db()
        self.assertEqual(c.estado, "En proceso")

    def test_cambio_de_fecha_exige_motivo_y_queda_en_historial(self):
        c = self.compromiso(estado="Pendiente")
        self.login("intermedio")
        nueva = (timezone.localdate() + timedelta(days=60)).isoformat()
        self.assertEqual(self.post_compromiso(reverse("editar_compromiso", args=[c.pk]), estado="Pendiente", fecha_comprometida=nueva).status_code, 200)
        self.assertEqual(self.post_compromiso(reverse("editar_compromiso", args=[c.pk]), estado="Pendiente", fecha_comprometida=nueva, observacion_cambio="Falta presupuesto").status_code, 302)
        self.assertIn("Cambio de fecha comprometida", c.historial.get().observacion)

    def test_vencido_proximo_y_filtro(self):
        hoy = timezone.localdate()
        vencido = self.compromiso(origen="ORIGEN-VENCIDO", estado="Pendiente", fecha_comprometida=hoy - timedelta(days=2))
        proximo = self.compromiso(origen="ORIGEN-PROXIMO", estado="En proceso", fecha_comprometida=hoy + timedelta(days=3))
        lejano = self.compromiso(origen="ORIGEN-LEJANO", fecha_comprometida=hoy + timedelta(days=40))
        hecho = self.compromiso(origen="ORIGEN-HECHO", estado="Realizado", fecha_comprometida=hoy - timedelta(days=5))
        self.assertEqual(vencido.situacion_plazo(hoy, 7), "vencido")
        self.assertEqual(proximo.situacion_plazo(hoy, 7), "proximo")
        self.assertEqual(lejano.situacion_plazo(hoy, 7), "al_dia")
        self.assertEqual(hecho.situacion_plazo(hoy, 7), "realizado")
        self.assertEqual(proximo.situacion_plazo(hoy, 2), "al_dia")  # umbral configurable
        self.login("minimo")
        r = self.client.get("/agenda/", {"plazo": "vencido"})
        self.assertContains(r, "ORIGEN-VENCIDO")
        self.assertNotContains(r, "ORIGEN-PROXIMO")
        self.assertNotContains(r, "ORIGEN-HECHO")
        r = self.client.get("/agenda/", {"plazo": "proximo"})
        self.assertContains(r, "ORIGEN-PROXIMO")
        self.assertNotContains(r, "ORIGEN-VENCIDO")
        self.assertContains(self.client.get(reverse("detalle_compromiso", args=[vencido.pk])), "Compromiso vencido")
        self.assertContains(self.client.get("/agenda/"), "fila-vencida")

    def test_umbral_desde_parametros(self):
        hoy = timezone.localdate()
        self.compromiso(origen="ORIGEN-10D", estado="Pendiente", fecha_comprometida=hoy + timedelta(days=10))
        self.login("minimo")
        with mock.patch("agenda.views.parametros", return_value={"dias_aviso_vencimiento": 15}):
            self.assertContains(self.client.get("/agenda/", {"plazo": "proximo"}), "ORIGEN-10D")
        with mock.patch("agenda.views.parametros", return_value={"dias_aviso_vencimiento": 5}):
            self.assertNotContains(self.client.get("/agenda/", {"plazo": "proximo"}), "ORIGEN-10D")

    def test_realizado_fuera_de_plazo(self):
        c = self.compromiso(estado="Realizado", fecha_comprometida=timezone.localdate() - timedelta(days=3))
        HistorialEstado.objects.create(compromiso=c, estado_anterior="En proceso", estado_nuevo="Realizado")
        self.assertEqual(c.situacion_plazo(), "fuera_plazo")

    def test_resumen_por_responsable_y_delegacion(self):
        p1, p2 = self.rows[1]["funcionarios"], self.rows[2]["funcionarios"]
        hoy = timezone.localdate()
        self.compromiso(responsable=p1, unidad=p1.delegacion, estado="Realizado")
        self.compromiso(responsable=p1, unidad=p1.delegacion, estado="Pendiente", fecha_comprometida=hoy - timedelta(days=1))
        self.compromiso(responsable=p2, unidad=p2.delegacion, estado="En proceso")
        self.login("minimo")
        r = self.client.get(reverse("resumen_agenda"))
        self.assertEqual(r.status_code, 200)
        filas = {f["nombre"]: f for f in r.context["por_responsable"]}
        self.assertEqual((filas[p1.nombre]["total"], filas[p1.nombre]["realizados"], filas[p1.nombre]["vencidos"], filas[p1.nombre]["por_realizado"]), (2, 1, 1, 50.0))
        delegaciones = {f["nombre"]: f for f in r.context["por_delegacion"]}
        self.assertEqual(delegaciones[p2.delegacion.nombre]["total"], 1)
        self.assertEqual(r.context["resumen"]["vencidos"], 1)
        self.assertContains(r, "Por responsable")
        self.assertContains(r, "Por delegación")

    def test_permisos_por_rol_e_historial_solo_lectura(self):
        c = self.compromiso()
        self.login("minimo")
        self.assertEqual(self.client.get(reverse("crear_compromiso")).status_code, 403)
        self.assertEqual(self.client.get(reverse("editar_compromiso", args=[c.pk])).status_code, 403)
        self.login("intermedio")
        self.assertEqual(self.client.get(reverse("borrar_compromiso", args=[c.pk])).status_code, 403)
        for role in ("total", "intermedio", "minimo"):
            u = User.objects.get(pk=self.users[role].pk)
            self.assertTrue(u.has_perm("agenda.view_historialestado"), role)
            for accion in ("add", "change", "delete"):
                self.assertFalse(u.has_perm(f"agenda.{accion}_historialestado"), (role, accion))

    def test_setup_roles_idempotente(self):
        antes = {g.name: set(g.permissions.values_list("pk", flat=True)) for g in Group.objects.all()}
        call_command("setup_roles", verbosity=0)
        call_command("setup_roles", verbosity=0)
        despues = {g.name: set(g.permissions.values_list("pk", flat=True)) for g in Group.objects.all()}
        self.assertEqual(antes, despues)

    def test_migracion_normaliza_sin_borrar(self):
        mig = import_module("agenda.migrations.0005_normalizar_estados_compromiso")
        a, b, ok = self.compromiso(), self.compromiso(), self.compromiso(estado="Pendiente")
        Compromiso.objects.filter(pk=a.pk).update(estado="realizada")
        Compromiso.objects.filter(pk=b.pk).update(estado="Algo raro", observaciones="nota previa")
        total = Compromiso.objects.count()
        with contextlib.redirect_stdout(io.StringIO()) as salida:
            mig.normalizar(django_apps, None)
        self.assertIn("Algo raro", salida.getvalue())
        a.refresh_from_db(); b.refresh_from_db(); ok.refresh_from_db()
        self.assertEqual((a.estado, b.estado, ok.estado), ("Realizado", "Pendiente", "Pendiente"))
        self.assertIn("nota previa", b.observaciones)
        self.assertIn("«Algo raro»", b.observaciones)
        self.assertEqual(b.historial.get().estado_anterior, "Algo raro")
        self.assertFalse(ok.historial.exists())
        self.assertEqual(Compromiso.objects.count(), total)


class ReglasClienteTests(BaseV41):
    def asignacion_payload(self, **cambios):
        a = self.rows[1]["asignaciones"]
        data = {"persona": a.persona_id, "catalogo": a.catalogo_id, "periodo": a.periodo_id, "meta": "5", "ponderador": "10", "fecha_asignacion": a.periodo.inicio.isoformat(), "observacion": "", "estado": "on"}
        data.update(cambios)
        return data

    def test_rn001_bloquea_sobre_100_y_advierte_bajo_100(self):
        self.login("total")
        antes = Meta.objects.count()
        r = self.client.post(reverse("catalog_crear", args=["asignaciones"]), self.asignacion_payload(ponderador="60"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "no puede superar 100 %")
        self.assertEqual(Meta.objects.count(), antes)
        r = self.client.post(reverse("catalog_crear", args=["asignaciones"]), self.asignacion_payload(ponderador="20"), follow=True)
        self.assertContains(r, "queda en 70 %")
        self.assertEqual(Meta.objects.count(), antes + 1)
        r = self.client.post(reverse("catalog_crear", args=["asignaciones"]), self.asignacion_payload(ponderador="30"), follow=True)
        self.assertNotContains(r, "Atención RN-001")

    def test_rn003_rn009_avance_calculado(self):
        a = self.rows[1]["asignaciones"]
        act = self.rows[1]["actividades"]
        a.catalogo.requiere_evidencia = False
        a.catalogo.save()
        a = Meta.objects.select_related("catalogo", "periodo").get(pk=a.pk)
        self.assertEqual(avance_calculado(a)[0], 0)  # actividad Pendiente no cuenta
        Actividad.objects.filter(pk=act.pk).update(estado="Validada")
        self.assertEqual(avance_calculado(a)[0], 1)
        a.catalogo.requiere_evidencia = True
        a.catalogo.save()
        a = Meta.objects.select_related("catalogo", "periodo").get(pk=a.pk)
        self.assertEqual(avance_calculado(a)[0], 0)  # evidencia "Registrada" no basta
        ev = Evidencia.objects.get(actividad=act)
        Evidencia.objects.filter(pk=ev.pk).update(estado="Rechazada")
        self.assertEqual(avance_calculado(a)[0], 0)
        Evidencia.objects.filter(pk=ev.pk).update(estado="Aprobada")
        self.assertEqual(avance_calculado(a)[0], 1)
        self.login("minimo")
        r = self.client.get(reverse("detalle_meta", args=[a.pk]))
        self.assertContains(r, "Avance calculado")
        with mock.patch("resultados.views._parametros", return_value={"fuente_avance": "calculado"}):
            r = self.client.get(reverse("detalle_meta", args=[a.pk]))
            self.assertEqual(r.context["pct_cumplimiento"], 10.0)  # 1 de 10
        Meta.objects.filter(pk=a.pk).update(avance=Decimal("5"))
        r = self.client.get(reverse("detalle_meta", args=[a.pk]))
        self.assertEqual(r.context["pct_cumplimiento"], 50.0)  # manual por defecto, sin perder el dato

    def test_rn007_meta_esperada_con_fecha_real(self):
        p = Periodo(inicio=date(2026, 1, 1), termino=date(2026, 1, 10), dias_computables=10)
        self.assertEqual(meta_esperada(p, date(2025, 12, 31)), 0.0)
        self.assertEqual(meta_esperada(p, date(2026, 1, 5)), 50.0)
        self.assertEqual(meta_esperada(p, date(2026, 3, 1)), 100.0)

    def test_rn013_periodo_cerrado_bloquea_datos(self):
        periodo = self.rows[1]["trimestres"]
        a = self.rows[1]["asignaciones"]
        Periodo.objects.filter(pk=periodo.pk).update(estado="Cerrado")
        self.login("total")
        form = forms.AsignacionForm(data=self.asignacion_payload(ponderador="40"), instance=a)
        self.assertFalse(form.is_valid())
        self.assertIn("cerrado", str(form.errors))
        r = self.client.post(reverse("catalog_borrar", args=["asignaciones", a.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Meta.objects.filter(pk=a.pk).exists())
        r = self.client.post(reverse("catalog_borrar", args=["evidencias", self.rows[1]["evidencias"].pk]))
        self.assertTrue(Evidencia.objects.filter(pk=self.rows[1]["evidencias"].pk).exists())
        r = self.client.post(reverse("catalog_crear", args=["asignaciones"]), self.asignacion_payload(ponderador="5"))
        self.assertEqual(r.status_code, 200)
        nueva = Actividad(codigo="X-CERRADO", fecha=date(2026, 2, 1), persona=a.persona, unidad=a.persona.delegacion, descripcion="d", accion="a", contacto="c", item="i", estado="Pendiente")
        with self.assertRaises(ValidationError):
            nueva.full_clean()
        self.assertEqual(self.client.post(reverse("catalog_borrar", args=["trimestres", periodo.pk])).status_code, 200)
        self.assertTrue(Periodo.objects.filter(pk=periodo.pk).exists())

    def trimestre_payload(self, periodo, **cambios):
        data = {"codigo": periodo.codigo, "nombre": periodo.nombre, "anio": periodo.anio, "numero": periodo.numero, "inicio": periodo.inicio.isoformat(), "termino": periodo.termino.isoformat(), "estado": periodo.estado}
        data.update(cambios)
        return data

    def test_rn013_reapertura_solo_acceso_total(self):
        periodo = self.rows[1]["trimestres"]
        Periodo.objects.filter(pk=periodo.pk).update(estado="Cerrado")
        periodo.refresh_from_db()
        url = reverse("catalog_editar", args=["trimestres", periodo.pk])
        self.login("total")
        self.assertEqual(self.client.post(url, self.trimestre_payload(periodo, nombre="Otro nombre")).status_code, 200)
        self.login("intermedio")
        self.assertEqual(self.client.post(url, self.trimestre_payload(periodo, estado="Abierto")).status_code, 200)
        periodo.refresh_from_db()
        self.assertEqual(periodo.estado, "Cerrado")
        self.login("total")
        self.assertEqual(self.client.post(url, self.trimestre_payload(periodo, estado="Abierto")).status_code, 302)
        periodo.refresh_from_db()
        self.assertEqual(periodo.estado, "Abierto")

    def test_rn012_maximo_tres_gestiones(self):
        base = self.rows[1]["gestiones"]
        campos = dict(fecha_ingreso=date(2026, 1, 5), fecha_atencion=date(2026, 1, 6), beneficiario=base.beneficiario, tipo=base.tipo, subtipo=base.subtipo, asignacion=base.asignacion, actuaciones="x")
        GestionSocial.objects.create(**campos)
        GestionSocial.objects.create(**campos)
        cuarta = GestionSocial(**campos)
        with self.assertRaises(ValidationError) as ctx:
            cuarta.full_clean()
        self.assertIn("RN-012", str(ctx.exception))
        cuarta.estado = "anulada"
        cuarta.full_clean()  # una anulada no cuenta
        base.full_clean()  # editar una existente sigue permitido

    def test_rn010_codigo_inmutable(self):
        act = self.rows[1]["actividades"]
        form = forms.ActividadForm(instance=act)
        self.assertTrue(form.fields["codigo"].disabled)
        self.assertFalse(forms.ActividadForm().fields["codigo"].disabled)
        self.login("total")
        r = self.client.get(reverse("catalog_editar", args=["actividades", act.pk]))
        self.assertContains(r, "Inmutable")

    def test_telefono_validado(self):
        v = self.rows[1]["vecinos"]
        for malo in ("abc", "12", "+56 9 1234 567x"):
            v.telefono = malo
            with self.assertRaises(ValidationError):
                v.full_clean()
        for bueno in ("+56 9 1234 5678", "512345678", "000000000"):
            v.telefono = bueno
            v.full_clean()

    def test_rn006_umbral_colectivo_en_tablero(self):
        self.login("minimo")
        periodo = self.rows[1]["trimestres"]
        Meta.objects.filter(pk=self.rows[1]["asignaciones"].pk).update(avance=Decimal("10"), ponderador=Decimal("100"))
        r = self.client.get(reverse("tablero_unidad"), {"periodo": periodo.pk})
        grupo = next(g for g in r.context["tablero"] if g["unidad"] == self.rows[1]["delegaciones"].nombre)
        self.assertEqual(grupo["colectivo"]["promedio"], 100.0)
        self.assertTrue(grupo["colectivo"]["cumple"])
        with mock.patch("resultados.views._parametros", return_value={"umbral_colectivo": 120}):
            r = self.client.get(reverse("tablero_unidad"), {"periodo": periodo.pk})
            grupo = next(g for g in r.context["tablero"] if g["unidad"] == self.rows[1]["delegaciones"].nombre)
            self.assertFalse(grupo["colectivo"]["cumple"])
            self.assertContains(r, "bajo el umbral")
        self.assertEqual(self.client.get(reverse("informe_resumen"), {"periodo": periodo.pk}).status_code, 200)
        self.assertEqual(self.client.get(reverse("tablero_unidad"), {"periodo": 999999}).status_code, 404)


class GestionClavesTests(BaseV41):
    def test_cambiar_clave_requiere_sesion(self):
        r = Client().get("/cuenta/clave/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])

    def test_cambiar_clave_propia(self):
        c = Client()
        self.assertTrue(c.login(username="v41_minimo", password=CLAVE))
        self.assertContains(c.get("/gestion/"), "Cambiar contraseña")
        r = c.post("/cuenta/clave/", {"old_password": "incorrecta", "new_password1": "OtraClaveSegura987!", "new_password2": "OtraClaveSegura987!"})
        self.assertEqual(r.status_code, 200)
        r = c.post("/cuenta/clave/", {"old_password": CLAVE, "new_password1": "OtraClaveSegura987!", "new_password2": "OtraClaveSegura987!"})
        self.assertRedirects(r, "/cuenta/clave/listo/")
        self.assertEqual(c.get("/gestion/").status_code, 200)  # la sesión sigue activa
        self.assertTrue(Client().login(username="v41_minimo", password="OtraClaveSegura987!"))

    @override_settings(AUTH_PASSWORD_VALIDATORS=VALIDADORES)
    def test_validadores_aplican_en_cambio(self):
        c = Client()
        c.login(username="v41_minimo", password=CLAVE)
        r = c.post("/cuenta/clave/", {"old_password": CLAVE, "new_password1": "12345678", "new_password2": "12345678"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors.get("new_password2"))

    def nuevo_funcionario(self):
        self.login("total")
        base = self.rows[1]["funcionarios"]
        data = {"usuario": "", "nuevo_usuario": "cuenta_nueva_v41", "nombres": "Nueva", "apellidos": "Ficticia", "rut": "95009999-0", "correo": "nueva@example.invalid", "cargo": base.cargo_id, "delegacion": base.delegacion_id, "estado": "Activo"}
        return self.client.post(reverse("catalog_crear", args=["funcionarios"]), data)

    def test_nuevo_usuario_lleva_a_establecer_clave(self):
        r = self.nuevo_funcionario()
        persona = Persona.objects.get(usuario__username="cuenta_nueva_v41")
        self.assertEqual(r["Location"], reverse("catalog_detalle", args=["funcionarios", persona.pk]) + "?nueva_cuenta=1")
        r = self.client.get(r["Location"])
        self.assertContains(r, "sin contraseña utilizable")
        self.assertContains(r, reverse("establecer_clave", args=[persona.pk]))
        self.assertNotContains(r, persona.usuario.password)

    def test_establecer_clave_solo_acceso_total(self):
        self.nuevo_funcionario()
        persona = Persona.objects.get(usuario__username="cuenta_nueva_v41")
        url = reverse("establecer_clave", args=[persona.pk])
        for role in ("intermedio", "minimo"):
            self.login(role)
            self.assertEqual(self.client.get(url).status_code, 403, role)
            self.assertEqual(self.client.post(url, {"new_password1": "ClaveInicial456!x", "new_password2": "ClaveInicial456!x"}).status_code, 403, role)
            self.assertNotContains(self.client.get(reverse("catalog_detalle", args=["funcionarios", persona.pk])), url)
        persona.usuario.refresh_from_db()
        self.assertFalse(persona.usuario.has_usable_password())
        self.login("total")
        self.assertEqual(self.client.get(url).status_code, 200)
        r = self.client.post(url, {"new_password1": "ClaveInicial456!x", "new_password2": "ClaveInicial456!x"}, follow=True)
        self.assertContains(r, "Contraseña inicial establecida")
        self.assertNotContains(r, "ClaveInicial456!x")
        persona.usuario.refresh_from_db()
        self.assertTrue(persona.usuario.has_usable_password())
        self.assertTrue(Client().login(username="cuenta_nueva_v41", password="ClaveInicial456!x"))

    @override_settings(AUTH_PASSWORD_VALIDATORS=VALIDADORES)
    def test_validadores_aplican_al_establecer(self):
        self.nuevo_funcionario()
        persona = Persona.objects.get(usuario__username="cuenta_nueva_v41")
        r = self.client.post(reverse("establecer_clave", args=[persona.pk]), {"new_password1": "password", "new_password2": "password"})
        self.assertEqual(r.status_code, 200)
        persona.usuario.refresh_from_db()
        self.assertFalse(persona.usuario.has_usable_password())

    def test_no_toma_cuentas_admin_ni_la_propia(self):
        admin = User.objects.create_user(username="admin_ficticio", password=CLAVE, is_staff=True)
        base = self.rows[1]["funcionarios"]
        persona = Persona.objects.create(usuario=admin, nombres="Admin", apellidos="Ficticio", nombre="Admin Ficticio", cargo=base.cargo, delegacion=base.delegacion)
        self.login("total")
        self.assertEqual(self.client.get(reverse("establecer_clave", args=[persona.pk])).status_code, 403)
        propia = Persona.objects.create(usuario=self.users["total"], nombres="Yo", apellidos="Total", nombre="Yo Total", cargo=base.cargo, delegacion=base.delegacion)
        self.assertRedirects(self.client.get(reverse("establecer_clave", args=[propia.pk])), reverse("cambiar_clave"))
        sin_cuenta = self.rows[1]["funcionarios"]
        self.assertEqual(self.client.get(reverse("establecer_clave", args=[999999])).status_code, 404)

    def test_detalle_muestra_estado_de_clave_sin_hash(self):
        self.login("minimo")
        persona = self.rows[1]["funcionarios"]
        r = self.client.get(reverse("catalog_detalle", args=["funcionarios", persona.pk]))
        self.assertContains(r, "Contraseña")
        self.assertContains(r, "Pendiente")
        self.assertNotContains(r, "pbkdf2")
