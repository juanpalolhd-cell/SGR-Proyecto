from django.core.management.base import BaseCommand
from sgr.demo_data import create_demo

class Command(BaseCommand):
    help = 'Añade muestras ficticias idempotentes para las 17 entidades; no elimina ni sobrescribe datos.'
    def handle(self, *args, **options):
        create_demo()
        self.stdout.write(self.style.SUCCESS('Muestras añadidas o conservadas. Sin cambios de contraseñas ni borrados. Las identidades de muestra no permiten iniciar sesión.'))
