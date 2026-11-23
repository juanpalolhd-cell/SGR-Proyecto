"""Tests for public login and role-based permissions."""

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(
    LOGIN_URL='/login/',
    LOGIN_EXEMPT_URLS=['/login/', '/logout/', '/admin/', '/static/'],
)
class LoginFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='demo',
            password='ClaveSegura99!',
            email='demo@example.com',
        )

    def test_home_redirects_anonymous(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_wrong_password(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'demo', 'password': 'mala'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Usuario o contraseña incorrectos', status_code=400)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_wrong_username(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'noexiste', 'password': 'ClaveSegura99!'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Usuario o contraseña incorrectos', status_code=400)

    def test_login_success(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'demo', 'password': 'ClaveSegura99!'},
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')
        # session authenticated
        response2 = self.client.get('/')
        self.assertEqual(response2.status_code, 200)

    def test_logout(self):
        self.client.login(username='demo', password='ClaveSegura99!')
        response = self.client.post(reverse('logout'), follow=False)
        self.assertIn(response.status_code, (200, 302))
        response2 = self.client.get('/')
        self.assertEqual(response2.status_code, 302)
        self.assertIn('/login/', response2['Location'])


@override_settings(
    LOGIN_URL='/login/',
    LOGIN_EXEMPT_URLS=['/login/', '/logout/', '/admin/', '/static/'],
)
class PermissionLevelsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('setup_roles')
        call_command(
            'setup_roles',
            create_users=True,
            password_total='TotalPass1234ab',
            password_intermedio='InterPass1234ab',
            password_minimo='MinimoPass1234a',
            email='demo@example.com',
        )

    def test_groups_exist(self):
        self.assertTrue(Group.objects.filter(name='Acceso total').exists())
        self.assertTrue(Group.objects.filter(name='Intermedio').exists())
        self.assertTrue(Group.objects.filter(name='Minimo').exists())

    def test_minimo_view_only_not_staff(self):
        u = User.objects.get(username='sgr_minimo')
        self.assertFalse(u.is_staff)
        self.assertFalse(u.is_superuser)
        self.assertTrue(u.has_perm('organizacion.view_unidad'))
        self.assertFalse(u.has_perm('actividades.add_actividad'))
        self.assertFalse(u.has_perm('actividades.delete_actividad'))
        self.assertFalse(u.has_perm('organizacion.add_unidad'))
        client = Client()
        self.assertTrue(client.login(username='sgr_minimo', password='MinimoPass1234a'))
        self.assertEqual(client.get('/').status_code, 200)
        self.assertEqual(client.get('/admin/').status_code, 302)  # admin login redirect

    def test_intermedio_can_edit_ops_not_org_delete(self):
        u = User.objects.get(username='sgr_intermedio')
        self.assertTrue(u.is_staff)
        self.assertFalse(u.is_superuser)
        self.assertTrue(u.has_perm('actividades.add_actividad'))
        self.assertTrue(u.has_perm('actividades.change_actividad'))
        self.assertTrue(u.has_perm('agenda.view_compromiso'))
        self.assertTrue(u.has_perm('resultados.change_meta'))
        self.assertFalse(u.has_perm('actividades.delete_actividad'))
        self.assertFalse(u.has_perm('organizacion.add_unidad'))
        self.assertFalse(u.has_perm('organizacion.change_unidad'))
        self.assertFalse(u.has_perm('organizacion.delete_unidad'))
        client = Client()
        self.assertTrue(client.login(username='sgr_intermedio', password='InterPass1234ab'))
        # staff reaches admin index (may be 200)
        resp = client.get('/admin/')
        self.assertIn(resp.status_code, (200, 302))

    def test_total_has_all_and_superuser(self):
        u = User.objects.get(username='sgr_total')
        self.assertTrue(u.is_staff)
        self.assertTrue(u.is_superuser)
        self.assertTrue(u.has_perm('organizacion.delete_unidad'))
        self.assertTrue(u.has_perm('actividades.delete_actividad'))
        client = Client()
        self.assertTrue(client.login(username='sgr_total', password='TotalPass1234ab'))
        self.assertEqual(client.get('/').status_code, 200)
        self.assertEqual(client.get('/admin/').status_code, 200)
