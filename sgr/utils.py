import json
from pathlib import Path


def load_json(filename):
    path = Path(__file__).resolve().parent.parent / "data" / filename
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def find_by_id(data, id_value):
    return next((item for item in data if item["id"] == id_value), None)