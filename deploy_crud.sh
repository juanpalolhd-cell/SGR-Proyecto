#!/bin/bash
# Despliegue SGR CRUD/busqueda. Requiere SSH o SSM con lab encendido.
set -euo pipefail
APP_DIR=/home/ubuntu/sgr
SERVICE=sgr
TGZ="${1:-/tmp/sgr_crud_deploy.tgz}"

sudo systemctl stop "$SERVICE" || true
sudo mkdir -p /var/backups/sgr
TS=$(date +%Y%m%d_%H%M%S)
sudo tar -czf "/var/backups/sgr/sgr_pre_crud_${TS}.tgz" -C "$(dirname "$APP_DIR")" "$(basename "$APP_DIR")" || true
sudo tar -xzf "$TGZ" -C "$APP_DIR"
cd "$APP_DIR"
if [ -f "$APP_DIR/venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$APP_DIR/venv/bin/activate"
fi
set -a
# shellcheck disable=SC1091
source /etc/sgr/sgr.env
set +a
python manage.py migrate --noinput
python - <<'PY'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','sgr.settings')
django.setup()
from organizacion.models import Unidad
from django.core.management import call_command
if Unidad.objects.count()==0:
    print('DB vacia: cargando seed_data')
    call_command('seed_data')
else:
    print(f'DB con {Unidad.objects.count()} unidades: no se ejecuta seed_data')
PY
python manage.py collectstatic --noinput
sudo systemctl start "$SERVICE"
sudo systemctl is-active "$SERVICE"
curl -s -o /dev/null -w 'login:%{http_code}\n' http://127.0.0.1/login/
