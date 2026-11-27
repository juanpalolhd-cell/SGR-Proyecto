#!/bin/bash
# Despliegue SGR V4.3 en EC2 sgr-app (sobre V4.2 + HTTPS): solicitudes de vecinos con consulta JJVV/cargo,
# flujo con % de avance, empresas contratistas y metas «solo presenciales». Migraciones solo aditivas.
# Uso (en la instancia, con el laboratorio de AWS Academy encendido):
#   sudo bash deploy_v43.sh /tmp/sgr_v43_deploy.tgz
# Opcional: TEST_EMAIL=direccion@dominio para enviar un correo de prueba al final (requiere SMTP en sgr.env).
# Variables opcionales: APP_DIR (/opt/sgr/app), ENV_FILE (/etc/sgr/sgr.env), SERVICE (sgr), VENV (autodetección).
# No crea ni restablece usuarios, no carga semillas y no imprime secretos.
set -euo pipefail
TGZ="${1:?Indique la ruta de sgr_v43_deploy.tgz}"
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
tar -czf "$BK/sgr-app-pre-v43-$TS.tgz" -C "$(dirname "$APP_DIR")" "$(basename "$APP_DIR")"
install -m 600 "$ENV_FILE" "$BK/sgr.env-pre-v43-$TS"
set -a; . "$ENV_FILE"; set +a
CNF=$(mktemp); chmod 600 "$CNF"; trap 'rm -f "$CNF"' EXIT
printf '[client]\nuser=%s\npassword=%s\nhost=%s\nport=%s\n' "${DB_USER:-}" "${DB_PASSWORD:-}" "${DB_HOST:-}" "${DB_PORT:-3306}" > "$CNF"
if command -v mysqldump >/dev/null; then
  mysqldump --defaults-extra-file="$CNF" --single-transaction --no-tablespaces --set-gtid-purged=OFF "${DB_NAME:?DB_NAME}" 2>/dev/null | gzip > "$BK/sgr_db-pre-v43-$TS.sql.gz" \
    || mysqldump --defaults-extra-file="$CNF" --single-transaction --no-tablespaces "${DB_NAME}" | gzip > "$BK/sgr_db-pre-v43-$TS.sql.gz"
  chmod 600 "$BK/sgr_db-pre-v43-$TS.sql.gz"
else
  echo "AVISO: no hay mysqldump; cree antes una instantánea manual de RDS (sgr-mysql-pre-v43-$TS)."; read -r -p "¿Continuar? (s/N) " r; [ "$r" = "s" ]
fi
ls -l "$BK" | grep "$TS"

echo "== 1b. Variables V4.2 en $ENV_FILE (solo se agregan las que faltan; nunca se muestran valores)"
[ -n "$(tail -c1 "$ENV_FILE")" ] && echo >> "$ENV_FILE"
agregar(){ grep -q "^$1=" "$ENV_FILE" || { echo "$1=$2" >> "$ENV_FILE"; echo "  agregada $1"; }; }
agregar SGR_CLAVE_TEMPORAL_HORAS 72
agregar DJANGO_PASSWORD_RESET_TIMEOUT 3600
agregar SGR_RECUPERACION_LIMITE 5
agregar SGR_RECUPERACION_VENTANA 3600
agregar SGR_CACHE db
if grep -rqsi "X-Forwarded-For" /etc/nginx/; then agregar SGR_PROXY_IP_HEADER HTTP_X_FORWARDED_FOR
else echo "  AVISO: nginx no envía X-Forwarded-For; el límite por IP contará a todos como 127.0.0.1."
     echo "         Agregue en el bloque location: proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for; y luego SGR_PROXY_IP_HEADER=HTTP_X_FORWARDED_FOR"; fi
for v in DJANGO_EMAIL_BACKEND DJANGO_EMAIL_HOST DJANGO_EMAIL_PORT DJANGO_EMAIL_USE_TLS DJANGO_EMAIL_HOST_USER DJANGO_EMAIL_HOST_PASSWORD DJANGO_DEFAULT_FROM_EMAIL SGR_URL_PUBLICA; do
  if grep -q "^$v=." "$ENV_FILE"; then echo "  $v: definida"; else echo "  $v: FALTA"; fi
done
grep -q "^DJANGO_EMAIL_BACKEND=.*smtp" "$ENV_FILE" || echo "  Sin SMTP: el sitio funciona, pero la recuperación por correo aparecerá como no disponible y la contraseña temporal no se enviará por correo."
chmod 600 "$ENV_FILE"
set -a; . "$ENV_FILE"; set +a

echo "== 2. Código nuevo (sin BD, venv ni secretos en el paquete)"
OWNER=$(stat -c '%U:%G' "$APP_DIR")
tar -xzf "$TGZ" --no-same-owner -C "$APP_DIR"
chown -R "$OWNER" "$APP_DIR"
find "$APP_DIR" -name '__pycache__' -type d -prune -exec rm -rf {} +

echo "== 3. Verificación, migraciones, permisos y estáticos"
cd "$APP_DIR"
export DJANGO_SETTINGS_MODULE=sgr.settings
"$PY" manage.py check
"$PY" manage.py showmigrations organizacion resultados solicitudes | tail -16
"$PY" manage.py migrate --noinput
[ "${SGR_CACHE:-}" = "db" ] && "$PY" manage.py createcachetable
"$PY" manage.py setup_roles            # SIN --create-users: no toca cuentas ni contraseñas
"$PY" manage.py collectstatic --noinput | tail -1

echo "== 4. Reinicio"
systemctl restart "$SERVICE"; sleep 3; systemctl is-active "$SERVICE"

echo "== 5. Prueba de humo (HTTPS local con el nombre público)"
HOST="${SGR_HOST:-44-213-253-178.sslip.io}"
fallo=0
chk(){ c=$(curl -s -m 15 --resolve "$HOST:443:127.0.0.1" -o /dev/null -w '%{http_code}' "https://$HOST$1"); echo "$1 -> $c (esperado $2)"; [ "$c" = "$2" ] || fallo=1; }
chk /login/ 200
chk /solicitudes/ 302
chk /solicitudes/nueva/ 302
chk /gestion/empresas/ 302
chk /agenda/ 302
chk /resultados/tablero/ 302
chk /static/css/style.css 200
chk /static/js/solicitud.js 200
c=$(curl -s -m 15 --resolve "$HOST:443:127.0.0.1" -o /dev/null -w '%{http_code}' "https://$HOST/cuenta/recuperar/"); echo "/cuenta/recuperar/ -> $c (200 con SMTP)"; case "$c" in 200|503) ;; *) fallo=1;; esac
loc=$(curl -s -m 15 -o /dev/null -w '%{http_code}' -H "Host: $HOST" "http://127.0.0.1/login/"); echo "http -> $loc (esperado 301)"; [ "$loc" = 301 ] || fallo=1
journalctl -u "$SERVICE" --since "-2 min" --no-pager | grep -i -E "error|traceback" && fallo=1 || true
if [ $fallo = 0 ]; then echo "DESPLIEGUE V4.3 OK. Respaldos: $BK/*-pre-v43-$TS*"; else
  echo "FALLÓ la prueba de humo. Para volver atrás:"
  echo "  sudo tar -xzf $BK/sgr-app-pre-v43-$TS.tgz -C $(dirname "$APP_DIR") && sudo systemctl restart $SERVICE"
  echo "  (migraciones V4.3 aditivas; para revertirlas: manage.py migrate solicitudes zero; resultados 0003; organizacion 0006)"
  echo "  y restaurar $BK/sgr.env-pre-v43-$TS en $ENV_FILE si fuera necesario"
  exit 1
fi
