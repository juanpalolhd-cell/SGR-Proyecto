#!/bin/bash
# Despliegue combinado: primero la V4.2 (deploy_v42.sh) y, si termina bien, HTTPS (activar_https.sh).
# Uso: sudo bash /tmp/sgr_kit/desplegar_v42_y_https.sh [nombre]      (por defecto 44-213-253-178.sslip.io)
# Variables opcionales: las de cada script (TEST_EMAIL, LE_EMAIL, HSTS_SECONDS, FORZAR_AUTOFIRMADO...).
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
echo "######## 1/2 Despliegue V4.2 ########"
bash "$D/deploy_v42.sh" "$D/sgr_v42_deploy.tgz"
echo "######## 2/2 HTTPS ########"
bash "$D/activar_https.sh" "${1:-}"
