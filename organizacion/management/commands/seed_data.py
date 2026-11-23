"""Backward-compatible safe name: legacy destructive seeding was retired in evaluation 3."""
from django.core.management.base import BaseCommand
from sgr.demo_data import create_demo

class Command(BaseCommand):
    help = 'Alias no destructivo de demo_evaluacion. Nunca elimina datos ni cambia contraseñas.'
    def handle(self, *args, **options):
        create_demo()
        self.stdout.write(self.style.SUCCESS('Muestras ficticias conservadas/añadidas sin borrados.'))
