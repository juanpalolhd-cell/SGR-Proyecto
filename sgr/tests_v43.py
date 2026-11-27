"""Pruebas V4.3: solicitudes de vecinos (JJVV y cargo, flujo con % de avance), empresas contratistas,
metas «solo presenciales» y columna de atenciones presenciales. Datos y cuentas sintéticos."""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from actividades.models import GestionSocial
from organizacion.models import Empresa, JuntaVecinos, Participacion, Vecino, resumen_jjvv
from resultados.calculos import avance_calculado
from resultados.models import CatalogoMeta, Meta, Periodo
from sgr.catalog import ALL_SPECS, SPECS
from sgr.demo_data import create_demo
from solicitudes import models as sm
from solicitudes.models import HistorialSolicitud, Solicitud, porcentaje_estado
from solicitudes.servicios import cambiar_estado

CLAVE = "SoloPruebaAislada123!"


class BaseV43(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rows = create_demo()
        call_command("setup_roles", verbosity=0)
        cls.users = {}
        for role, group in [("total", "Acceso total"), ("intermedio", "Intermedio"), ("minimo", "Minimo")]:
            u = User.objects.create_user(username="v43_" + role, password=CLAVE)
            u.groups.add(Group.objects.get(name=group))
            cls.users[role] = u
        hoy = timezone.localdate()
        cls.persona = cls.rows[1]["funcionarios"]
        cls.periodo = Periodo.objects.create(codigo="V43-T", nombre="Período prueba V4.3", anio=hoy.year, numero=1, inicio=hoy - timedelta(days=30), termino=hoy + timedelta(days=30), dias_computables=61, estado="Abierto")
        cls.catalogo = CatalogoMeta.objects.create(codigo="V43-CAT", nombre="Solicitudes atendidas", descripcion="x", tipo="individual", unidad_medida="solicitudes")
        cls.meta = Meta.objects.create(periodo=cls.periodo, persona=cls.persona, catalogo=cls.catalogo, item="Solicitudes atendidas", unidad="solicitudes", meta=Decimal("4"), ponderador=Decimal("5"))
        cls.vecino = cls.rows[1]["vecinos"]
        cls.vecino_sin = Vecino.objects.create(rut="11111111-1", nombres="Sin", apellidos="Junta", telefono="+56911111111", correo="sin@example.invalid", direccion="Calle 1", territorio=cls.vecino.territorio)
        ter = cls.vecino.territorio
        cls.junta = JuntaVecinos.objects.create(codigo="V43-JV", nombre="JJVV Prueba V4.3", direccion="Sede 1", delegacion=ter.delegacion, territorio=ter, fecha_constitucion=hoy - timedelta(days=900))
        Participacion.objects.filter(vecino=cls.vecino).delete()
        Participacion.objects.create(vecino=cls.vecino, junta=cls.junta, dirigente=True, cargo="Tesorero", fecha_incorporacion=hoy - timedelta(days=100))
        cls.empresa = Empresa.objects.create(nombre="Contratista Ficticia SpA", rubro="Mantención")

    def login(self, role):
        self.client.force_login(self.users[role])

    def solicitud(self, **extra):
        datos = dict(vecino=self.vecino_sin, asunto="Luminaria apagada", descripcion="Poste sin luz", responsable=self.persona, asignacion=self.meta)
        datos.update(extra)
        return Solicitud.objects.create(**datos)

    def datos_form(self, **cambios):
        d = {"fecha_ingreso": timezone.localdate().isoformat(), "vecino": self.vecino.pk, "asunto": "Bache en la calle", "descripcion": "Bache frente a la sede", "responsable": self.persona.pk, "asignacion": self.meta.pk, "empresa": "", "fecha_comprometida": "", "observaciones": ""}
        d.update(cambios)
        return d


class PorcentajesYTransicionesTests(BaseV43):
    def test_porcentajes_por_defecto(self):
        esperado = {"Ingresada": 10, "En supervisión/verificación": 25, "Derivada a empresa": 50, "En ejecución": 75, "Verificación de realizado": 90, "Cerrada": 100, "Rechazada": 0, "Anulada": 0}
        self.assertEqual({e: porcentaje_estado(e) for e in esperado}, esperado)

    def test_porcentajes_configurables_en_parametros(self):
        with mock.patch("solicitudes.models.parametros", return_value={"solicitud_avance": {"Derivada a empresa": 40}}):
            self.assertEqual(porcentaje_estado("Derivada a empresa"), 40)
            self.assertEqual(porcentaje_estado("Ingresada"), 10)

    def test_flujo_completo_un_paso_a_la_vez(self):
        s = self.solicitud()
        u = self.users["intermedio"]
        cambiar_estado(s, sm.SUPERVISION, u)
        cambiar_estado(s, sm.DERIVADA, u, empresa=self.empresa)
        cambiar_estado(s, sm.EJECUCION, u)
        cambiar_estado(s, sm.VERIFICACION, u)
        cambiar_estado(s, sm.CERRADA, u)
        s.refresh_from_db()
        self.assertEqual((s.estado, s.porcentaje, s.fecha_cierre), (sm.CERRADA, 100, timezone.localdate()))
        self.assertEqual(list(s.historial.values_list("porcentaje", flat=True)), [25, 50, 75, 90, 100])
        with self.assertRaises(ValidationError):
            cambiar_estado(s, sm.VERIFICACION, u, "reabrir")

    def test_no_se_puede_saltar_etapas(self):
        s = self.solicitud()
        for destino in (sm.DERIVADA, sm.EJECUCION, sm.CERRADA):
            with self.assertRaises(ValidationError):
                cambiar_estado(s, destino, empresa=self.empresa)
        self.assertEqual(Solicitud.objects.get(pk=s.pk).estado, sm.INGRESADA)

    def test_devolver_exige_observacion(self):
        s = self.solicitud(estado=sm.VERIFICACION, empresa=self.empresa)
        with self.assertRaises(ValidationError):
            cambiar_estado(s, sm.EJECUCION, self.users["total"], "")
        cambiar_estado(s, sm.EJECUCION, self.users["total"], "La obra quedó incompleta")
        h = s.historial.last()
        self.assertEqual((h.estado_anterior, h.estado_nuevo, h.porcentaje), (sm.VERIFICACION, sm.EJECUCION, 75))
        self.assertIn("incompleta", h.observacion)

    def test_derivar_exige_empresa(self):
        s = self.solicitud(estado=sm.SUPERVISION)
        with self.assertRaises(ValidationError):
            cambiar_estado(s, sm.DERIVADA)
        cambiar_estado(s, sm.DERIVADA, empresa=self.empresa)
        self.assertEqual(Solicitud.objects.get(pk=s.pk).empresa, self.empresa)

    def test_rechazar_y_anular_exigen_observacion_y_son_terminales(self):
        s = self.solicitud()
        with self.assertRaises(ValidationError):
            cambiar_estado(s, sm.RECHAZADA)
        cambiar_estado(s, sm.RECHAZADA, observacion="No corresponde a la delegación")
        s.refresh_from_db()
        self.assertEqual((s.porcentaje, s.estados_siguientes), (0, []))

    def test_asignacion_debe_ser_del_responsable(self):
        otro = self.rows[2]["funcionarios"]
        s = Solicitud(vecino=self.vecino_sin, asunto="x", descripcion="y", responsable=otro, asignacion=self.meta)
        with self.assertRaises(ValidationError) as ctx:
            s.full_clean()
        self.assertIn("asignacion", ctx.exception.message_dict)

    def test_periodo_cerrado_bloquea_cambios_rn013(self):
        s = self.solicitud(estado=sm.SUPERVISION)
        Periodo.objects.filter(pk=self.periodo.pk).update(estado="Cerrado")
        s = Solicitud.objects.get(pk=s.pk)
        with self.assertRaises(ValidationError):
            cambiar_estado(s, sm.DERIVADA, empresa=self.empresa)
        self.login("total")
        r = self.client.get(reverse("detalle_solicitud", args=[s.pk]))
        self.assertContains(r, "RN-013")
        self.assertNotContains(r, "Registrar cambio de estado")


class JJVVTests(BaseV43):
    def test_resumen_con_cargo_y_sin_cargo(self):
        self.assertEqual(resumen_jjvv(self.vecino)["texto"], "Pertenece a JJVV JJVV Prueba V4.3 – cargo Tesorero")
        r = resumen_jjvv(self.vecino_sin)
        self.assertFalse(r["pertenece"])
        self.assertIn("Sin cargo", r["texto"])

    def test_endpoint_consulta_jjvv(self):
        self.login("minimo")
        d = self.client.get(reverse("vecino_jjvv", args=[self.vecino.pk])).json()
        self.assertEqual((d["con_cargo"], d["junta"], d["cargo"]), (True, "JJVV Prueba V4.3", "Tesorero"))
        self.client.logout()
        self.assertEqual(self.client.get(reverse("vecino_jjvv", args=[self.vecino.pk])).status_code, 302)

    def test_ingreso_con_cargo_informa_y_permite_continuar(self):
        self.login("intermedio")
        r = self.client.post(reverse("crear_solicitud"), self.datos_form(), follow=True)
        s = Solicitud.objects.get(asunto="Bache en la calle")
        self.assertEqual((s.estado, s.porcentaje, s.junta, s.cargo_jjvv), (sm.INGRESADA, 10, self.junta, "Tesorero"))
        self.assertContains(r, "cargo Tesorero")
        h = HistorialSolicitud.objects.get(solicitud=s)
        self.assertEqual((h.estado_nuevo, h.porcentaje, h.usuario), (sm.INGRESADA, 10, self.users["intermedio"]))
        self.assertIn("Consulta JJVV", h.observacion)

    def test_ingreso_sin_cargo(self):
        self.login("total")
        self.client.post(reverse("crear_solicitud"), self.datos_form(vecino=self.vecino_sin.pk, asunto="Poda"))
        s = Solicitud.objects.get(asunto="Poda")
        self.assertEqual((s.junta, s.cargo_jjvv), (None, ""))

    def test_detalle_vecino_muestra_participaciones(self):
        self.login("minimo")
        r = self.client.get(reverse("catalog_detalle", args=["vecinos", self.vecino.pk]))
        self.assertContains(r, "Juntas de vecinos y cargo")
        self.assertContains(r, "Tesorero")
        self.assertContains(r, "JJVV Prueba V4.3")


class PermisosYPantallasTests(BaseV43):
    def test_pantallas_200_para_acceso_total(self):
        s = self.solicitud()
        self.login("total")
        for url in [reverse("lista_solicitudes"), reverse("crear_solicitud"), reverse("detalle_solicitud", args=[s.pk]), reverse("editar_solicitud", args=[s.pk]), reverse("catalog_lista", args=["empresas"]), reverse("catalog_crear", args=["empresas"]), reverse("catalog_index"), reverse("tablero_unidad")]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertContains(self.client.get("/"), reverse("lista_solicitudes"))

    def test_minimo_solo_lectura(self):
        s = self.solicitud()
        self.login("minimo")
        self.assertEqual(self.client.get(reverse("lista_solicitudes")).status_code, 200)
        self.assertEqual(self.client.get(reverse("detalle_solicitud", args=[s.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("crear_solicitud")).status_code, 403)
        self.assertEqual(self.client.post(reverse("estado_solicitud", args=[s.pk]), {"nuevo_estado": sm.SUPERVISION}).status_code, 403)
        self.assertEqual(self.client.get(reverse("editar_solicitud", args=[s.pk])).status_code, 403)
        self.assertEqual(Solicitud.objects.get(pk=s.pk).estado, sm.INGRESADA)

    def test_intermedio_opera_cambio_de_estado_por_el_sitio(self):
        s = self.solicitud()
        self.login("intermedio")
        r = self.client.post(reverse("estado_solicitud", args=[s.pk]), {"nuevo_estado": sm.SUPERVISION, "observacion": ""})
        self.assertRedirects(r, reverse("detalle_solicitud", args=[s.pk]))
        self.assertEqual(Solicitud.objects.get(pk=s.pk).estado, sm.SUPERVISION)
        r = self.client.post(reverse("estado_solicitud", args=[s.pk]), {"nuevo_estado": sm.INGRESADA, "observacion": ""})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "obligatoria")
        self.assertEqual(Solicitud.objects.get(pk=s.pk).estado, sm.SUPERVISION)

    def test_editar_solicitud_terminal_no_permitido(self):
        s = self.solicitud(estado=sm.ANULADA)
        self.login("total")
        r = self.client.get(reverse("editar_solicitud", args=[s.pk]))
        self.assertRedirects(r, reverse("detalle_solicitud", args=[s.pk]))

    def test_empresas_crud_en_gestion(self):
        self.login("total")
        r = self.client.post(reverse("catalog_crear", args=["empresas"]), {"nombre": "Otra Contratista", "rut": "", "rubro": "Aseo", "contacto": "", "telefono": "", "correo": "", "estado": "on"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Empresa.objects.filter(nombre="Otra Contratista").exists())
        self.login("intermedio")
        self.assertEqual(self.client.get(reverse("catalog_lista", args=["empresas"])).status_code, 200)
        self.assertEqual(self.client.get(reverse("catalog_crear", args=["empresas"])).status_code, 403)

    def test_siguen_17_entidades_de_la_evaluacion(self):
        self.assertEqual(len(SPECS), 17)
        self.assertIn("empresas", ALL_SPECS)

    def test_setup_roles_idempotente_permisos_v43(self):
        call_command("setup_roles", verbosity=0)
        call_command("setup_roles", verbosity=0)
        inter = set(Group.objects.get(name="Intermedio").permissions.values_list("codename", flat=True))
        minimo = set(Group.objects.get(name="Minimo").permissions.values_list("codename", flat=True))
        total = set(Group.objects.get(name="Acceso total").permissions.values_list("codename", flat=True))
        self.assertTrue({"view_solicitud", "add_solicitud", "change_solicitud", "view_historialsolicitud", "view_empresa"} <= inter)
        self.assertFalse({"delete_solicitud", "add_empresa", "change_historialsolicitud"} & inter)
        self.assertEqual({c for c in minimo if c.endswith(("solicitud", "empresa"))}, {"view_solicitud", "view_historialsolicitud", "view_empresa"})
        self.assertTrue({"add_empresa", "change_empresa", "delete_empresa", "add_solicitud"} <= total)
        self.assertNotIn("change_historialsolicitud", total)


class AvanceYPresencialesTests(BaseV43):
    def test_solicitudes_cerradas_suman_al_avance_calculado(self):
        self.solicitud(estado=sm.CERRADA, fecha_cierre=timezone.localdate(), empresa=self.empresa)
        self.solicitud(estado=sm.RECHAZADA)
        self.solicitud(estado=sm.EJECUCION, empresa=self.empresa)
        total, detalle = avance_calculado(Meta.objects.get(pk=self.meta.pk))
        self.assertEqual((total, detalle["solicitudes"], detalle["solicitudes_parcial"]), (1, 1, 0.0))

    def test_avance_parcial_opcional(self):
        self.solicitud(estado=sm.CERRADA, fecha_cierre=timezone.localdate(), empresa=self.empresa)
        self.solicitud(estado=sm.EJECUCION, empresa=self.empresa)
        self.solicitud(estado=sm.ANULADA)
        with mock.patch("sgr.parametros.load_json", return_value={"parametros": {"solicitudes_avance_parcial": True}}):
            total, detalle = avance_calculado(Meta.objects.get(pk=self.meta.pk))
        self.assertEqual((total, detalle["solicitudes_parcial"]), (1.75, 0.75))

    def test_cerrada_fuera_del_periodo_no_suma(self):
        self.solicitud(estado=sm.CERRADA, fecha_cierre=self.periodo.termino + timedelta(days=5), empresa=self.empresa)
        self.assertEqual(avance_calculado(Meta.objects.get(pk=self.meta.pk))[1]["solicitudes"], 0)

    def _gestion(self, visita, meta):
        sub = self.rows[1]["subtipos"]
        hoy = timezone.localdate()
        return GestionSocial.objects.create(fecha_ingreso=hoy, fecha_atencion=hoy, beneficiario=self.vecino, tipo=sub.tipo_atencion, subtipo=sub, asignacion=meta, visita=visita, actuaciones="Atención", estado="atendida")

    def test_meta_solo_presenciales_cuenta_visitas(self):
        cat = CatalogoMeta.objects.create(codigo="V43-PRES", nombre="Atenciones en terreno", descripcion="x", tipo="individual", unidad_medida="atenciones", solo_presenciales=True)
        meta = Meta.objects.create(periodo=self.periodo, persona=self.persona, catalogo=cat, item=cat.nombre, unidad="atenciones", meta=Decimal("10"), ponderador=Decimal("5"))
        self._gestion(True, meta); self._gestion(True, meta); self._gestion(False, meta)
        total, detalle = avance_calculado(meta)
        self.assertEqual((total, detalle["gestiones"], detalle["solo_presenciales"]), (2, 2, True))
        meta_normal = Meta.objects.get(pk=self.meta.pk)
        self._gestion(True, meta_normal); self._gestion(False, meta_normal)
        self.assertEqual(avance_calculado(meta_normal)[1]["gestiones"], 2)

    def test_tablero_muestra_presenciales(self):
        self._gestion(True, self.meta); self._gestion(False, self.meta)
        self.login("minimo")
        r = self.client.get(reverse("tablero_unidad") + f"?periodo={self.periodo.pk}")
        self.assertContains(r, "Atenciones presenciales")
        fila = [f for u in r.context["tablero"] for f in u["miembros"] if f["persona_id"] == self.persona.pk][0]
        self.assertEqual(fila["presenciales"], 1)

    def test_formulario_catalogo_tiene_solo_presenciales(self):
        self.login("total")
        self.assertContains(self.client.get(reverse("catalog_crear", args=["metas"])), "solo_presenciales")
