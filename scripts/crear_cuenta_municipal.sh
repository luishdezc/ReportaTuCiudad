#!/usr/bin/env bash
# Crea (o actualiza) la cuenta oficial municipal simulada en DynamoDB.
# Uso: ./scripts/crear_cuenta_municipal.sh municipio@reportatuciudad.mx "UnaClaveSegura123"
set -euo pipefail

CORREO="${1:?Falta el correo de la cuenta municipal}"
CLAVE="${2:?Falta la contrasena}"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ/infra"

TABLA="$(terraform output -raw tabla_usuarios)"
REGION="$(terraform output -raw url_api | sed -E 's|.*execute-api\.([^.]+)\.amazonaws.*|\1|')"

HASH="$(python3 - "$CLAVE" <<'PY'
import hashlib, sys, uuid
password = sys.argv[1]
salt = uuid.uuid4().hex
print("%s$%s" % (salt, hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()))
PY
)"

USER_ID="usr_municipio"
FECHA="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

aws dynamodb put-item \
  --region "$REGION" \
  --table-name "$TABLA" \
  --item "{
    \"userId\":       {\"S\": \"$USER_ID\"},
    \"email\":        {\"S\": \"$CORREO\"},
    \"nombre\":       {\"S\": \"Cuenta municipal\"},
    \"colonia\":      {\"S\": \"Ayuntamiento\"},
    \"rol\":          {\"S\": \"municipio\"},
    \"passwordHash\": {\"S\": \"$HASH\"},
    \"creadoEn\":     {\"S\": \"$FECHA\"}
  }"

echo "Cuenta municipal lista: $CORREO (entra en admin.html)"
