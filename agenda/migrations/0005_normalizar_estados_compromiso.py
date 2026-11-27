"""Normaliza el estado libre de Compromiso a los 4 estados controlados, sin borrar nada.

- Los valores reconocidos (sin importar mayúsculas, tildes o guiones bajos) se llevan al estado canónico.
- Los valores desconocidos pasan a «Pendiente»; el valor original queda anotado en observaciones
  y en el historial de estados, y se informa en la salida de migrate.
- La reversa restaura el valor original desde el historial creado aquí.
"""
import unicodedata

from django.db import migrations
from django.utils import timezone

MARCA = "[Migración 0005]"
SINONIMOS = {
    "ingresado": "Ingresado", "ingresada": "Ingresado", "nuevo": "Ingresado", "nueva": "Ingresado",
    "pendiente": "Pendiente",
    "en proceso": "En proceso", "en curso": "En proceso", "en progreso": "En proceso", "proceso": "En proceso",
    "realizado": "Realizado", "realizada": "Realizado", "completado": "Realizado", "completada": "Realizado",
    "cumplido": "Realizado", "cumplida": "Realizado", "finalizado": "Realizado", "finalizada": "Realizado",
}


def _norm(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return " ".join(texto.lower().replace("_", " ").replace("-", " ").split())


def normalizar(apps, schema_editor):
    Compromiso = apps.get_model("agenda", "Compromiso")
    Historial = apps.get_model("agenda", "HistorialEstado")
    desconocidos = []
    for c in Compromiso.objects.all().order_by("pk"):
        original = c.estado or ""
        canonico = SINONIMOS.get(_norm(original))
        if canonico == original:
            continue
        if canonico is None:
            canonico = "Pendiente"
            desconocidos.append((c.pk, original))
            nota = f"{MARCA} Estado original «{original}» no reconocido; se asignó «Pendiente»."
        else:
            nota = f"{MARCA} Estado «{original}» normalizado a «{canonico}»."
        c.observaciones = (c.observaciones + "\n" if c.observaciones else "") + nota
        c.estado = canonico
        c.save(update_fields=["estado", "observaciones"])
        Historial.objects.create(compromiso=c, usuario=None, fecha=timezone.now(), estado_anterior=original[:50], estado_nuevo=canonico, observacion=nota)
    if desconocidos:
        print(f"\n  {MARCA} {len(desconocidos)} compromiso(s) con estado desconocido pasaron a Pendiente:")
        for pk, original in desconocidos:
            print(f"    - Compromiso {pk}: «{original}»")


def revertir(apps, schema_editor):
    Compromiso = apps.get_model("agenda", "Compromiso")
    Historial = apps.get_model("agenda", "HistorialEstado")
    for h in Historial.objects.filter(observacion__startswith=MARCA).order_by("-id"):
        c = Compromiso.objects.filter(pk=h.compromiso_id).first()
        if c is None:
            continue
        c.estado = h.estado_anterior
        lineas = [l for l in c.observaciones.split("\n") if not l.startswith(MARCA)]
        c.observaciones = "\n".join(lineas)
        c.save(update_fields=["estado", "observaciones"])
        h.delete()


class Migration(migrations.Migration):
    dependencies = [("agenda", "0004_historial_estado_y_estados")]
    operations = [migrations.RunPython(normalizar, revertir)]
