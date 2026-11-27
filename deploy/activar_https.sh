#!/bin/bash
# SGR - Activar HTTPS en la instancia EC2 sgr-app (nginx + gunicorn, Amazon Linux 2023).
# Uso (en la instancia, después de desplegar la V4.2):
#   sudo bash activar_https.sh                      # usa 44-213-253-178.sslip.io
#   sudo bash activar_https.sh sgr.midominio.cl     # otro nombre que ya apunte a la IP elástica
# Variables opcionales:
#   LE_EMAIL=correo            correo para avisos de Let's Encrypt (si no, se registra sin correo)
#   HSTS_SECONDS=3600          max-age inicial de HSTS (moderado; súbalo cuando todo funcione)
#   FORZAR_AUTOFIRMADO=1       no intenta Let's Encrypt (solo certificado autofirmado)
#   LE_STAGING=1               usa el entorno de pruebas de Let's Encrypt
#   PUBLIC_IP (44.213.253.178), ENV_FILE (/etc/sgr/sgr.env), SERVICE (sgr), APP_DIR (/opt/sgr/app),
#   UPSTREAM (se detecta del proxy_pass actual de nginx), STATIC_DIR (se detecta).
# Es idempotente: se puede volver a ejecutar. No imprime secretos ni valores de sgr.env.
set -euo pipefail
PUBLIC_IP="${PUBLIC_IP:-44.213.253.178}"
HOST="${1:-${PUBLIC_IP//./-}.sslip.io}"
ENV_FILE="${ENV_FILE:-/etc/sgr/sgr.env}"
SERVICE="${SERVICE:-sgr}"
APP_DIR="${APP_DIR:-/opt/sgr/app}"
HSTS_SECONDS="${HSTS_SECONDS:-3600}"
NGINX_DIR="${NGINX_DIR:-/etc/nginx}"
CONF="$NGINX_DIR/conf.d/sgr_https.conf"
WEBROOT=/var/www/letsencrypt
TLS_DIR=/etc/sgr/tls
TS=$(date +%Y%m%d_%H%M%S)
BK="/var/backups/sgr/https-pre-$TS"

[ "$(id -u)" = 0 ] || { echo "Ejecute con sudo."; exit 1; }
[[ "$HOST" =~ ^[A-Za-z0-9.-]+$ ]] || { echo "Nombre de host no válido: $HOST"; exit 1; }
command -v nginx >/dev/null || { echo "No se encontró nginx."; exit 1; }
[ -f "$ENV_FILE" ] || { echo "No existe $ENV_FILE"; exit 1; }
export PUBLIC_IP
echo "Nombre: $HOST   IP elástica: $PUBLIC_IP"

echo "== 0. DNS"
RES=$(getent ahostsv4 "$HOST" | awk 'NR==1{print $1}' || true)
if [ "$RES" = "$PUBLIC_IP" ]; then echo "  $HOST -> $RES (correcto)"
else echo "  AVISO: $HOST resuelve a '${RES:-nada}', no a $PUBLIC_IP. Let's Encrypt probablemente fallará (se usará autofirmado)."; fi

echo "== 1. Respaldos en $BK"
mkdir -p "$BK"; chmod 700 /var/backups/sgr "$BK"
tar -czf "$BK/nginx.tgz" -C "$(dirname "$NGINX_DIR")" "$(basename "$NGINX_DIR")"
install -m 600 "$ENV_FILE" "$BK/sgr.env"
echo "  nginx.tgz y sgr.env respaldados"

echo "== 2. Detectar la configuración actual del SGR en nginx"
NT=$(mktemp -d); trap 'rm -rf "$NT"' EXIT
nginx -T 2>/dev/null > "$NT/nginx_T.txt" || { echo "nginx -T falló; revise la configuración actual."; exit 1; }
python3 - "$NT" "$CONF" <<'PY'
import re, sys, os, shlex
nt, ours = sys.argv[1], sys.argv[2]
txt = open(os.path.join(nt, "nginx_T.txt"), encoding="utf-8", errors="replace").read()
files = {}
for part in re.split(r"^# configuration file ", txt, flags=re.M)[1:]:
    name, _, body = part.partition("\n")
    files[name.rstrip(":").strip()] = re.sub(r"(?m)#.*$", "", body)
cands = [f for f, b in files.items() if re.search(r"\bproxy_pass\s+[^;]+;", b)]
pref = [f for f in cands if f != ours] or cands
out = {"SGR_CONF": "", "UP_DET": "", "STATIC_DET": "", "IP_EN_OTRO": "0"}
if pref:
    f = pref[0]; b = files[f]; out["SGR_CONF"] = f
    out["UP_DET"] = re.search(r"\bproxy_pass\s+([^;]+);", b).group(1).strip()
    m = re.search(r"location\s+\^?~?\s*/static/?\s*\{[^}]*?\b(alias|root)\s+([^;]+);", b, re.S)
    if m:
        p = m.group(2).strip().rstrip("/")
        out["STATIC_DET"] = p if m.group(1) == "alias" else p + "/static"
    host = re.sub(r"^https?://", "", out["UP_DET"]).split("/")[0]
    blk = re.search(r"upstream\s+" + re.escape(host) + r"\s*\{[^}]*\}", b, re.S) if host and not host.startswith("unix:") else None
    open(os.path.join(nt, "upstream.inc"), "w").write(blk.group(0) + "\n" if blk else "")
for f, b in files.items():
    if f in (ours, out["SGR_CONF"]): continue
    if re.search(r"server_name[^;]*\b" + re.escape(os.environ.get("PUBLIC_IP", "44.213.253.178")) + r"\b", b): out["IP_EN_OTRO"] = "1"
with open(os.path.join(nt, "det.sh"), "w") as fh:
    for k, v in out.items(): fh.write(f"{k}={shlex.quote(v)}\n")
PY
. "$NT/det.sh"
UPSTREAM="${UPSTREAM:-$UP_DET}"
[ -n "$UPSTREAM" ] || { echo "No se encontró proxy_pass hacia gunicorn. Indique UPSTREAM=http://127.0.0.1:8000 (por ejemplo)."; exit 1; }
VENV=""; for v in /opt/sgr/venv "$APP_DIR/venv" "$APP_DIR/.venv" /opt/sgr/.venv; do [ -z "$VENV" ] && [ -x "$v/bin/python" ] && VENV="$v"; done
if [ -z "${STATIC_DIR:-}" ]; then
  STATIC_DIR="$STATIC_DET"
  if [ -z "$STATIC_DIR" ] && [ -n "$VENV" ]; then
    STATIC_DIR=$(cd "$APP_DIR" && set -a && . "$ENV_FILE" && set +a && DJANGO_SETTINGS_MODULE=sgr.settings "$VENV/bin/python" -c "import django;django.setup();from django.conf import settings;print(settings.STATIC_ROOT or '')" 2>/dev/null || true)
  fi
fi
echo "  Archivo actual del SGR: ${SGR_CONF:-(no encontrado)}"
echo "  Gunicorn (proxy_pass): $UPSTREAM"
echo "  Estáticos: ${STATIC_DIR:-(no detectados; se servirán por Django)}"

proxy_block(){ cat <<EOF
        proxy_pass $UPSTREAM;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_read_timeout 60s;
EOF
}
static_block(){ [ -n "$STATIC_DIR" ] && cat <<EOF
    location /static/ {
        alias $STATIC_DIR/;
        expires 7d;
        access_log off;
    }
EOF
  return 0; }
escribir_fase1(){ { echo "# SGR HTTPS - fase 1 (solo validación de Let's Encrypt). Generado $TS por activar_https.sh"
  # El bloque upstream solo se copia si el archivo anterior ya no está activo (evita «duplicate upstream»).
  [ "$SGR_CONF" = "$CONF" ] && cat "$NT/upstream.inc" 2>/dev/null || true
  cat <<EOF
server {
    listen 80;
    server_name $HOST;
    client_max_body_size 20m;
    location ^~ /.well-known/acme-challenge/ { root $WEBROOT; default_type text/plain; }
$(static_block)
    location / {
$(proxy_block)
    }
}
EOF
  } > "$CONF"; }
recargar_o_revertir(){ if ! nginx -t 2>&1 | tail -2; then echo "nginx -t falló: se restaura la configuración anterior."; rm -f "$CONF"; tar -xzf "$BK/nginx.tgz" -C "$(dirname "$NGINX_DIR")"; nginx -t && systemctl reload nginx; exit 1; fi; systemctl reload nginx; sleep 2; }

echo "== 3. Certificado"
mkdir -p "$WEBROOT/.well-known/acme-challenge" "$TLS_DIR"; chmod 755 "$WEBROOT"
TIPO=""; LE_LIVE="/etc/letsencrypt/live/$HOST"
if [ "${FORZAR_AUTOFIRMADO:-0}" != 1 ] && [ -s "$LE_LIVE/fullchain.pem" ] && openssl x509 -checkend 2592000 -noout -in "$LE_LIVE/fullchain.pem" >/dev/null 2>&1; then
  TIPO=letsencrypt; echo "  Certificado de Let's Encrypt vigente (más de 30 días); no se pide otro."
elif [ "${FORZAR_AUTOFIRMADO:-0}" != 1 ]; then
  if ! command -v certbot >/dev/null; then
    echo "  Instalando certbot..."
    if command -v dnf >/dev/null && dnf install -y -q certbot >/dev/null 2>&1; then echo "  certbot instalado con dnf"
    else
      command -v dnf >/dev/null && dnf install -y -q python3-pip augeas-libs >/dev/null 2>&1 || true
      python3 -m venv /opt/certbot && /opt/certbot/bin/pip install -q --upgrade pip certbot && ln -sf /opt/certbot/bin/certbot /usr/local/bin/certbot && echo "  certbot instalado con pip en /opt/certbot" || echo "  AVISO: no se pudo instalar certbot."
    fi
  fi
  if command -v certbot >/dev/null; then
    escribir_fase1; recargar_o_revertir
    REG=(--register-unsafely-without-email); [ -n "${LE_EMAIL:-}" ] && REG=(-m "$LE_EMAIL")
    STG=(); [ "${LE_STAGING:-0}" = 1 ] && STG=(--test-cert)
    if certbot certonly --webroot -w "$WEBROOT" -d "$HOST" --agree-tos --non-interactive --keep-until-expiring "${REG[@]}" "${STG[@]}"; then
      [ -s "$LE_LIVE/fullchain.pem" ] && TIPO=letsencrypt
    fi
  fi
  [ -n "$TIPO" ] || echo "  AVISO: Let's Encrypt no entregó certificado (puerto 80 cerrado desde Internet, DNS o límite de emisión)."
fi
if [ -z "$TIPO" ]; then
  TIPO=autofirmado
  if [ ! -s "$TLS_DIR/$HOST.crt" ] || ! openssl x509 -checkend 2592000 -noout -in "$TLS_DIR/$HOST.crt" >/dev/null 2>&1; then
    openssl req -x509 -newkey rsa:2048 -nodes -days 365 -subj "/CN=$HOST" \
      -addext "subjectAltName=DNS:$HOST,IP:$PUBLIC_IP" -keyout "$TLS_DIR/$HOST.key" -out "$TLS_DIR/$HOST.crt" 2>/dev/null
    chmod 600 "$TLS_DIR/$HOST.key"
  fi
  echo "  *** Se usa un CERTIFICADO AUTOFIRMADO: el navegador mostrará una advertencia. ***"
  echo "  *** Vuelva a ejecutar el script cuando Let's Encrypt sea posible.              ***"
fi
if [ "$TIPO" = letsencrypt ]; then CRT="$LE_LIVE/fullchain.pem"; KEY="$LE_LIVE/privkey.pem"; else CRT="$TLS_DIR/$HOST.crt"; KEY="$TLS_DIR/$HOST.key"; fi
echo "  Tipo de certificado: $TIPO"

echo "== 4. Configuración final de nginx (443, redirección 80 -> 443, HSTS)"
DESACT=""
if [ -n "$SGR_CONF" ] && [ "$SGR_CONF" != "$CONF" ]; then
  case "$SGR_CONF" in
    "$NGINX_DIR"/conf.d/*.conf) DESACT="$SGR_CONF.desactivado-https-$TS"; mv "$SGR_CONF" "$DESACT"; echo "  $SGR_CONF queda desactivado (renombrado a $(basename "$DESACT"); el respaldo está en $BK)";;
    *) echo "  AVISO: el bloque actual del SGR está en $SGR_CONF (no en conf.d). No se modifica: sigue atendiendo http://$PUBLIC_IP sin redirección."
       echo "         Para redirigir, reemplace allí 'location / {...}' por: return 301 https://$HOST\$request_uri;"; IP_EN_OTRO=1;;
  esac
fi
HSTS_LINE=""; [ "$TIPO" = letsencrypt ] && [ "$HSTS_SECONDS" -gt 0 ] && HSTS_LINE="    add_header Strict-Transport-Security \"max-age=$HSTS_SECONDS\" always;"
NOMBRES80="$HOST"; [ "$IP_EN_OTRO" = 1 ] || NOMBRES80="$HOST $PUBLIC_IP"
{ echo "# SGR HTTPS. Generado $TS por activar_https.sh (certificado: $TIPO). Respaldo previo: $BK"
  cat "$NT/upstream.inc" 2>/dev/null || true
  cat <<EOF
# HTTP: solo validación de Let's Encrypt y redirección permanente a HTTPS.
server {
    listen 80;
    server_name $NOMBRES80;
    location ^~ /.well-known/acme-challenge/ { root $WEBROOT; default_type text/plain; }
    location / { return 301 https://$HOST\$request_uri; }
}
# HTTP local (pruebas desde la propia instancia); rechaza otros orígenes.
server {
    listen 80;
    server_name 127.0.0.1 localhost;
    allow 127.0.0.1; allow ::1; deny all;
$(static_block)
    location / {
$(proxy_block)
    }
}
server {
    listen 443 ssl;
    http2 on;
    server_name $HOST;
    ssl_certificate $CRT;
    ssl_certificate_key $KEY;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SGRSSL:10m;
    ssl_session_timeout 1d;
$HSTS_LINE
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy same-origin always;
    client_max_body_size 20m;
$(static_block)
    location / {
$(proxy_block)
    }
}
EOF
} > "$CONF"
if ! nginx -t 2>&1 | tail -2; then
  echo "nginx -t falló: se restaura la configuración anterior."; rm -f "$CONF"; [ -n "$DESACT" ] && mv "$DESACT" "$SGR_CONF"
  nginx -t && systemctl reload nginx; exit 1
fi

echo "== 5. Renovación automática"
if [ "$TIPO" = letsencrypt ]; then
  mkdir -p /etc/letsencrypt/renewal-hooks/deploy
  printf '#!/bin/sh\nsystemctl reload nginx\n' > /etc/letsencrypt/renewal-hooks/deploy/sgr-reload-nginx.sh; chmod 755 /etc/letsencrypt/renewal-hooks/deploy/sgr-reload-nginx.sh
  if systemctl list-unit-files 2>/dev/null | grep -q '^certbot-renew.timer'; then systemctl enable --now certbot-renew.timer >/dev/null 2>&1 || true; echo "  certbot-renew.timer activo"
  else
    CB=$(command -v certbot)
    printf '[Unit]\nDescription=Renovar certificados Lets Encrypt (SGR)\n[Service]\nType=oneshot\nExecStart=%s renew --quiet\n' "$CB" > /etc/systemd/system/sgr-certbot-renew.service
    printf '[Unit]\nDescription=Renovar certificados dos veces al dia (SGR)\n[Timer]\nOnCalendar=*-*-* 03,15:17:00\nRandomizedDelaySec=1h\nPersistent=true\n[Install]\nWantedBy=timers.target\n' > /etc/systemd/system/sgr-certbot-renew.timer
    systemctl daemon-reload; systemctl enable --now sgr-certbot-renew.timer >/dev/null 2>&1 || true; echo "  sgr-certbot-renew.timer activo (dos veces al día)"
  fi
else echo "  (autofirmado: sin renovación automática; vence en 365 días)"; fi

echo "== 6. Variables en $ENV_FILE (sin mostrar valores)"
[ -n "$(tail -c1 "$ENV_FILE")" ] && echo >> "$ENV_FILE"
python3 - "$ENV_FILE" "$HOST" <<'PY'
import sys, re
path, host = sys.argv[1], sys.argv[2]
lines = open(path, encoding="utf-8").read().splitlines()
def get(k):
    for l in lines:
        if l.startswith(k + "="): return l.split("=", 1)[1].strip().strip('"').strip("'")
    return None
def put(k, v, msg):
    for i, l in enumerate(lines):
        if l.startswith(k + "="):
            if l == f"{k}={v}": print(f"  {k}: sin cambios"); return
            lines[i] = f"{k}={v}"; print(f"  {k}: {msg}"); return
    lines.append(f"{k}={v}"); print(f"  {k}: agregada")
def merge(k, item):
    cur = [x.strip() for x in (get(k) or "").split(",") if x.strip()]
    if item in cur: print(f"  {k}: ya incluía el nombre"); return
    put(k, ",".join(cur + [item]), "se agregó el nombre nuevo (se conservan los anteriores)")
merge("DJANGO_ALLOWED_HOSTS", host)
merge("DJANGO_CSRF_TRUSTED_ORIGINS", "https://" + host)
put("SGR_URL_PUBLICA", "https://" + host, "actualizada a https")
put("DJANGO_SECURE_PROXY_SSL_HEADER", "True", "actualizada")
put("DJANGO_SECURE_COOKIES", "True", "actualizada")
put("DJANGO_SECURE_SSL_REDIRECT", "False", "actualizada (nginx ya redirige)")
put("DJANGO_SECURE_HSTS_SECONDS", "0", "actualizada (HSTS lo envía nginx)")
put("SGR_PROXY_IP_HEADER", "HTTP_X_FORWARDED_FOR", "actualizada")
open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
PY
chmod 600 "$ENV_FILE"

echo "== 7. Reinicio"
systemctl reload nginx
systemctl restart "$SERVICE"; sleep 3; systemctl is-active "$SERVICE"

# Script de reversión.
cat > "$BK/revertir.sh" <<EOF
#!/bin/bash
# Revierte activar_https.sh del $TS: nginx y sgr.env vuelven a su estado previo.
set -e
rm -f "$CONF"${DESACT:+ "$DESACT"}
tar -xzf "$BK/nginx.tgz" -C "$(dirname "$NGINX_DIR")"
install -m 600 "$BK/sgr.env" "$ENV_FILE"
nginx -t && systemctl reload nginx
systemctl restart "$SERVICE"
echo "Revertido. El sitio vuelve a http://$PUBLIC_IP/ (los certificados en /etc/letsencrypt y $TLS_DIR se conservan)."
EOF
chmod 700 "$BK/revertir.sh"

echo "== 8. Prueba de humo (con --resolve hacia esta instancia)"
fallo=0; R=(--resolve "$HOST:443:127.0.0.1" --resolve "$HOST:80:127.0.0.1" -s -m 15)
CA=(); [ "$TIPO" = autofirmado ] && CA=(--cacert "$CRT")
[ "$TIPO" = letsencrypt ] && [ "${LE_STAGING:-0}" = 1 ] && CA=(-k)
ok(){ echo "  OK   $1"; }; mal(){ echo "  FALLA $1"; fallo=1; }
c=$(curl "${R[@]}" "${CA[@]}" -o /dev/null -w '%{http_code}' "https://$HOST/login/"); [ "$c" = 200 ] && ok "https://$HOST/login/ -> 200" || mal "https://$HOST/login/ -> $c"
loc=$(curl "${R[@]}" -o /dev/null -w '%{http_code} %{redirect_url}' "http://$HOST/login/"); [ "$loc" = "301 https://$HOST/login/" ] && ok "http://$HOST/login/ -> 301 https" || mal "redirección 80->443: $loc"
if [ "$IP_EN_OTRO" != 1 ]; then loc=$(curl -s -m 15 -o /dev/null -w '%{http_code} %{redirect_url}' -H "Host: $PUBLIC_IP" "http://127.0.0.1/"); [[ "$loc" == "301 https://$HOST/"* ]] && ok "http://$PUBLIC_IP/ -> 301 https" || mal "redirección IP: $loc"; fi
c=$(curl "${R[@]}" "${CA[@]}" -o /dev/null -w '%{http_code}' "https://$HOST/admin/login/"); [ "$c" = 200 ] && ok "admin -> 200" || mal "admin -> $c"
c=$(curl "${R[@]}" "${CA[@]}" -o /dev/null -w '%{http_code}' "https://$HOST/static/css/style.css"); [ "$c" = 200 ] && ok "estáticos -> 200" || mal "estáticos -> $c"
c=$(curl "${R[@]}" "${CA[@]}" -o /dev/null -w '%{http_code}' "https://$HOST/cuenta/recuperar/"); case "$c" in 200|503) ok "recuperar -> $c (503 = sin SMTP)";; *) mal "recuperar -> $c";; esac
H=$(curl "${R[@]}" "${CA[@]}" -D - -o /dev/null "https://$HOST/login/")
if [ -n "$HSTS_LINE" ]; then echo "$H" | grep -qi "^strict-transport-security: max-age=$HSTS_SECONDS" && ok "HSTS max-age=$HSTS_SECONDS" || mal "falta HSTS"; fi
echo "$H" | grep -i '^set-cookie: csrftoken' | grep -qi 'secure' && ok "cookie CSRF con Secure" || mal "cookie CSRF sin Secure"
# POST con CSRF: usuario inexistente y contraseña aleatoria (nunca credenciales reales).
J="$NT/cookies"; P=$(curl "${R[@]}" "${CA[@]}" -c "$J" "https://$HOST/login/")
TOK=$(echo "$P" | grep -o 'name="csrfmiddlewaretoken" value="[^"]*"' | head -1 | sed 's/.*value="//;s/"$//')
c=$(curl "${R[@]}" "${CA[@]}" -b "$J" -o /dev/null -w '%{http_code}' -e "https://$HOST/login/" --data-urlencode "csrfmiddlewaretoken=$TOK" --data-urlencode "username=prueba_https_inexistente" --data-urlencode "password=$(openssl rand -hex 12)" "https://$HOST/login/")
case "$c" in 200|400) ok "POST con CSRF aceptado (login rechazado como corresponde: $c)";; *) mal "POST con CSRF -> $c";; esac
c=$(curl "${R[@]}" "${CA[@]}" -o /dev/null -w '%{http_code}' -e "https://$HOST/login/" -d "username=x&password=y" "https://$HOST/login/"); [ "$c" = 403 ] && ok "POST sin CSRF -> 403" || mal "POST sin CSRF -> $c"
journalctl -u "$SERVICE" --since "-2 min" --no-pager 2>/dev/null | grep -i -E "traceback" && mal "errores en el journal" || true

echo
echo "Para revertir:  sudo bash $BK/revertir.sh"
if [ $fallo = 0 ]; then
  echo "HTTPS ACTIVO ($TIPO). URL: https://$HOST/"
  [ "$TIPO" = autofirmado ] && echo "AVISO: certificado autofirmado; el navegador mostrará una advertencia y HSTS no se activó."
  echo "Desde fuera verifique: curl -I https://$HOST/login/   (el puerto 443 debe estar abierto en el grupo de seguridad)"
else
  echo "FALLÓ la prueba de humo. Revise lo anterior o revierta con el comando indicado."; exit 1
fi
