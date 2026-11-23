"""Compatibility regressions for historical URLs after evaluation-3 validation."""
from django.contrib.auth.models import User, Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from sgr.demo_data import create_demo

class LegacyRouteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rows=create_demo();call_command("setup_roles",verbosity=0)
        cls.total=User.objects.create_user(username="legacy_total")
        cls.total.groups.add(Group.objects.get(name="Acceso total"))
        cls.minimo=User.objects.create_user(username="legacy_minimo")
        cls.minimo.groups.add(Group.objects.get(name="Minimo"))
    def test_search_and_existing_read_routes(self):
        self.client.force_login(self.minimo)
        for url in ("/buscar/?q=ficticia","/organizacion/unidades/","/organizacion/personas/","/actividades/","/actividades/evidencias/","/agenda/","/resultados/"):
            self.assertEqual(self.client.get(url).status_code,200)
    def test_old_crud_routes_use_complete_forms(self):
        self.client.force_login(self.total)
        for name in ("crear_unidad","crear_persona","crear_cargo","crear_actividad","crear_evidencia","crear_meta","crear_periodo"):
            with self.subTest(name=name):
                url=reverse(name);self.assertEqual(self.client.get(url).status_code,200)
                self.assertEqual(self.client.post(url,{}).status_code,200)
        self.assertContains(self.client.get(reverse("crear_actividad")),"fecha_compromiso")
    def test_old_write_routes_reject_query_only(self):
        self.client.force_login(self.minimo)
        for name in ("crear_unidad","crear_persona","crear_cargo","crear_actividad","crear_evidencia","crear_meta","crear_periodo"):
            self.assertEqual(self.client.get(reverse(name)).status_code,403)
            self.assertEqual(self.client.post(reverse(name),{}).status_code,403)
    def test_old_protected_delete_is_friendly(self):
        self.client.force_login(self.total)
        url=reverse("borrar_unidad",args=[self.rows[1]["delegaciones"].pk])
        self.assertEqual(self.client.post(url).status_code,200)
        self.assertContains(self.client.post(url),"registros relacionados")
