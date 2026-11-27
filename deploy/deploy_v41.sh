#!/bin/bash
# Despliegue SGR V4.1 (tubo de trabajo, reglas del cliente, gestión de contraseñas) en EC2 sgr-app.
# Uso (en la instancia, con el laboratorio de AWS Academy encendido):
#   sudo bash deploy_v41.sh /tmp/sgr_v41_deploy.tgz
# Variables opcionales: APP_DIR (/opt/sgr/app), ENV_FILE (/etc/sgr/sgr.env), SERVICE (sgr), VENV (autodetección).
# No crea ni restablece usuarios, no carga semillas y no imprime secretos.
set -euo pipefail
TGZ="${1:?Indique la ruta de sgr_v41_deploy.tgz}"
APP_DIR="${APP_DIR:-/opt/sgr/app}"
ENV_FILE="${ENV_FILE:-/etc/sgr/sgr.env}"
SERVICE="${SERVICE:-sgr}"
BK=/var/backups/sgr
TS=$(date +%Y%m%d_%H%M%S)

[ -d "$APP_DIR" ] || { echo "No existe $APP_DIR"; exit 1; }
[ -f "$ENV_FILE" ] || { echo "No existe $ENV_FILE"; exit 1; }
if [ -f "$TGZ.sha256" ]; then (cd "$(dirname "$TGZ")" && sha256sum -c "$(basename "$TGZ").sha256"); fi

VENV="${VENV:-}"
for v in /opt/sgr/venv "$APP_DIR/venv" "$APP_DIR/.venv" /opt/sgr/.venv; do
  [ -z "$VENV" ] && [ -x "$v/bin/python" ] && VENV="$v"
done
PY="${VENV:+$VENV/bin/python}"; PY="${PY:-python3}"
echo "Python: $PY"

echo "== 1. Respaldos en $BK (permisos restringidos)"
mkdir -p "$BK"; chmod 700 "$BK"
tar -czf "$BK/sgr-app-pre-v41-$TS.tgz" -C "$(dirname "$APP_DIR")" "$(basename "$APP_DIR")"
install -m 600 "$ENV_FILE" "$BK/sgr.env-pre-v41-$TS"
set -a; . "$ENV_FILE"; set +a
CNF=$(mktemp); chmod 600 "$CNF"; trap 'rm -f "$CNF"' EXIT
printf '[client]\nuser=%s\npassword=%s\nhost=%s\nport=%s\n' "${DB_USER:-}" "${DB_PASSWORD:-}" "${DB_HOST:-}" "${DB_PORT:-3306}" > "$CNF"
if command -v mysqldump >/dev/null; then
  mysqldump --defaults-extra-file="$CNF" --single-transaction --no-tablespaces --set-gtid-purged=OFF "${DB_NAME:?DB_NAME}" 2>/dev/null | gzip > "$BK/sgr_db-pre-v41-$TS.sql.gz" \
    || mysqldump --defaults-extra-file="$CNF" --single-transaction --no-tablespaces "${DB_NAME}" | gzip > "$BK/sgr_db-pre-v41-$TS.sql.gz"
  chmod 600 "$BK/sgr_db-pre-v41-$TS.sql.gz"
else
  echo "AVISO: no hay mysqldump; cree antes una instantánea manual de RDS (sgr-mysql-pre-v41-$TS)."; read -r -p "¿Continuar? (s/N) " r; [ "$r" = "s" ]
fi
ls -l "$BK" | grep "$TS"

echo "== 2. Código nuevo (sin BD, venv ni secretos en el paquete)"
OWNER=$(stat -c '%U:%G' "$APP_DIR")
tar -xzf "$TGZ" --no-same-owner -C "$APP_DIR"
chown -R "$OWNER" "$APP_DIR"
find "$APP_DIR" -name '__pycache__' -type d -prune -exec rm -rf {} +

echo "== 3. Verificación, migraciones, permisos y estáticos"
cd "$APP_DIR"
export DJANGO_SETTINGS_MODULE=sgr.settings
"$PY" manage.py check
"$PY" manage.py showmigrations agenda actividades organizacion | tail -12
"$PY" manage.py migrate --noinput
"$PY" manage.py setup_roles            # SIN --create-users: no toca cuentas ni contraseñas
"$PY" manage.py collectstatic --noinput | tail -1

echo "== 4. Reinicio"
systemctl restart "$SERVICE"; sleep 3; systemctl is-active "$SERVICE"

echo "== 5. Prueba de humo"
fallo=0
chk(){ c=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1$1"); echo "$1 -> $c (esperado $2)"; [ "$c" = "$2" ] || fallo=1; }
chk /login/ 200
chk /agenda/ 302
chk /agenda/resumen/ 302
chk /cuenta/clave/ 302
chk /resultados/tablero/ 302
chk /static/css/style.css 200
journalctl -u "$SERVICE" --since "-2 min" --no-pager | grep -i -E "error|traceback" && fallo=1 || true
if [ $fallo = 0 ]; then echo "DESPLIEGUE V4.1 OK. Respaldos: $BK/*-pre-v41-$TS*"; else
  echo "FALLÓ la prueba de humo. Para volver atrás:"
  echo "  sudo tar -xzf $BK/sgr-app-pre-v41-$TS.tgz -C $(dirname "$APP_DIR") && sudo systemctl restart $SERVICE"
  echo "  (las migraciones nuevas son aditivas; si hiciera falta: manage.py migrate agenda 0003, actividades 0005, organizacion 0004)"
  exit 1
fi
