"""Counts only: no credentials, hashes, or personal record values in output."""
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from sgr.catalog import SPECS

class Command(BaseCommand):
    help = 'Cuenta registros por entidad y formularios históricos por completar; no modifica datos.'
    def handle(self, *args, **options):
        for slug, (title, form_class, _) in SPECS.items():
            count = invalid = 0
            for obj in form_class._meta.model.objects.all():
                count += 1
                bad = False
                try: obj.full_clean()
                except ValidationError: bad = True
                if any(getattr(obj, field, None) in (None, '') for field in getattr(form_class,'required_fields',())):
                    bad = True
                if slug == 'funcionarios' and not obj.usuario_id:
                    bad = True
                if slug == 'roles' and not obj.grupo_id:
                    bad = True
                if slug == 'delegaciones' and not obj.delegado_id:
                    bad = True
                if bad: invalid += 1
            self.stdout.write(f'{title}: {count} registros; {invalid} requieren completar/validar datos históricos.')
