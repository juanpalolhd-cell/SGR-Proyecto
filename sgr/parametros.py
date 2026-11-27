"""Parámetros operativos configurables sin cambiar código (data/resultados.json → "parametros")."""
from sgr.utils import load_json

DEFAULTS = {
    "tope_ponderado": 150,
    "umbral_colectivo": 80,
    "maximo_cumplimiento": 100,
    "regla_semaforo_ambar": 60,
    "dias_aviso_vencimiento": 7,
    "fuente_avance": "manual",
}


def parametros():
    """Devuelve los parámetros del archivo, completando con valores por defecto."""
    valores = dict(DEFAULTS)
    try:
        valores.update(load_json("resultados.json").get("parametros", {}))
    except Exception:
        pass
    return valores
