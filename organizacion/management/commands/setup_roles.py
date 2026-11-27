"""Create permission groups Acceso total / Intermedio / Minimo and optional users."""

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

ORG_APPS = ('organizacion',)
EDIT_APPS = ('actividades', 'agenda', 'resultados', 'solicitudes')
ALL_APPS = ORG_APPS + EDIT_APPS
# Modelos de auditoría: todos los roles solo pueden verlos; nadie los edita desde el sitio.
SOLO_LECTURA = ('historialestado', 'historialsolicitud')
# Modelos internos de seguridad (V4.2): ningún grupo recibe permisos; se gestionan solo desde las vistas de cuenta.
INTERNOS = ('estadoclave',)


def _perms_for_apps(app_labels, actions=None):
    qs = Permission.objects.filter(content_type__app_label__in=app_labels)
    if actions:
        from django.db.models import Q
        q = Q()
        for a in actions:
            q |= Q(codename__startswith=f'{a}_')
        qs = qs.filter(q)
    qs = qs.select_related('content_type')
    return [p for p in qs if p.content_type.model not in INTERNOS and (p.content_type.model not in SOLO_LECTURA or p.codename.startswith('view_'))]


class Command(BaseCommand):
    help = 'Crea grupos de permisos SGR y, opcionalmente, usuarios de demostración.'

    def add_arguments(self, parser):
        parser.add_argument('--create-users', action='store_true')
        parser.add_argument('--email', default='demo@example.invalid')
        parser.add_argument('--password-total', default='')
        parser.add_argument('--password-intermedio', default='')
        parser.add_argument('--password-minimo', default='')

    @transaction.atomic
    def handle(self, *args, **options):
        view_all = _perms_for_apps(ALL_APPS, actions=('view',))
        # Intermedio: view everything + add/change on edit apps; no delete; no org write
        intermedio_extra = _perms_for_apps(EDIT_APPS, actions=('add', 'change'))
        # Acceso total: all perms on project apps
        total_perms = _perms_for_apps(ALL_APPS)

        g_total, _ = Group.objects.get_or_create(name='Acceso total')
        g_total.permissions.set(total_perms)
        g_inter, _ = Group.objects.get_or_create(name='Intermedio')
        g_inter.permissions.set(list({*view_all, *intermedio_extra}))
        g_min, _ = Group.objects.get_or_create(name='Minimo')
        g_min.permissions.set(view_all)

        self.stdout.write(self.style.SUCCESS(
            f'Grupos listos: Acceso total={g_total.permissions.count()}, '
            f'Intermedio={g_inter.permissions.count()}, Minimo={g_min.permissions.count()}'
        ))

        if not options['create_users']:
            return

        specs = [
            ('sgr_total', options['password_total'], g_total, True, True),
            ('sgr_intermedio', options['password_intermedio'], g_inter, True, False),
            ('sgr_minimo', options['password_minimo'], g_min, False, False),
        ]
        for username, password, group, is_staff, is_superuser in specs:
            if not password:
                self.stderr.write(f'Salta {username}: falta --password-*')
                continue
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': options['email']},
            )
            if not created:
                self.stdout.write(self.style.WARNING(f'Usuario {username} conservado sin cambios.'))
                continue
            user.email = options['email']
            user.is_active = True
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.set_password(password)
            user.save()
            user.groups.set([group])
            action = 'creado' if created else 'actualizado'
            self.stdout.write(self.style.SUCCESS(f'Usuario {username} {action}'))
