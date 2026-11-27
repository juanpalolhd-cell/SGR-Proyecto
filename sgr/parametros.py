"""Parámetros operativos configurables sin cambiar código (data/resultados.json → "parametros")."""
from sgr.utils import load_json

DEFAULTS = {
    "tope_ponderado": 150,
    "umbral_colectivo": 80,
    "maximo_cumplimiento": 100,
    "regla_semaforo_ambar": 60,
    "dias_aviso_vencimiento": 7,
    "fuente_avance": "manual",
    # V4.3: porcentaje de avance de una solicitud según su estado (configurable sin cambiar código).
    "solicitud_avance": {
        "Ingresada": 10,
        "En supervisión/verificación": 25,
        "Derivada a empresa": 50,
        "En ejecución": 75,
        "Verificación de realizado": 90,
        "Cerrada": 100,
        "Rechazada": 0,
        "Anulada": 0,
    },
    # V4.3: si es true, las solicitudes abiertas aportan su porcentaje parcial al avance calculado.
    "solicitudes_avance_parcial": False,
}


def parametros():
    """Devuelve los parámetros del archivo, completando con valores por defecto."""
    valores = dict(DEFAULTS)
    try:
        valores.update(load_json("resultados.json").get("parametros", {}))
    except Exception:
        pass
    return valores
