from django.contrib import admin
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from organizacion.models import Delegacion, Item, PerfilUsuario, Rol, SubAtencion, TipoAtencion
from sgr.utils import find_by_id, load_json


class AdminComplianceTests(SimpleTestCase):
    def test_required_models_exist_and_are_registered(self):
        required = [
            Delegacion,
            Rol,
            PerfilUsuario,
            Item,
            TipoAtencion,
            SubAtencion,
        ]
        for model in required:
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)


@override_settings(
    LOGIN_URL="/login/",
    LOGIN_EXEMPT_URLS=["/login/", "/logout/", "/admin/", "/static/"],
)
class SmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_data")
        call_command("setup_roles")
        user = User.objects.create_user(username="smoke", password="SmokePass1234ab")
        from django.contrib.auth.models import Group
        user.groups.add(Group.objects.get(name="Minimo"))

    def setUp(self):
        self.assertTrue(self.client.login(username="smoke", password="SmokePass1234ab"))

    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sistema de Gestión de Resultados")

    def test_organizacion_routes_are_accessible(self):
        urls = [
            "/organizacion/unidades/",
            "/organizacion/personas/",
            "/organizacion/unidades/1/",
            "/organizacion/personas/1/",
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIn(response.status_code, [200, 404])

    def test_resultados_routes_are_accessible(self):
        urls = [
            "/resultados/",
            "/resultados/tablero/",
            "/resultados/informe/",
            "/resultados/meta/1/",
            "/resultados/persona/1/",
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIn(response.status_code, [200, 404])

    def test_invalid_detail_routes_return_404(self):
        self.assertEqual(self.client.get("/organizacion/unidades/999/").status_code, 404)
        self.assertEqual(self.client.get("/resultados/meta/999/").status_code, 404)
        self.assertEqual(self.client.get("/resultados/persona/999/").status_code, 404)


class JsonFixturesTests(SimpleTestCase):
    def test_json_data_files_load_and_have_expected_keys(self):
        organizacion = load_json("organizacion.json")
        self.assertIn("unidades", organizacion)
        self.assertIn("personas", organizacion)
        self.assertIn("cargos", organizacion)

        resultados = load_json("resultados.json")
        self.assertIn("metas", resultados)
        self.assertIn("periodos", resultados)
        self.assertIn("parametros", resultados)

        self.assertIsNotNone(find_by_id(organizacion["personas"], 1))
        self.assertIsNotNone(find_by_id(resultados["metas"], 1))
