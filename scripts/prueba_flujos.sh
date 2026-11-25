#!/usr/bin/env bash
# Prueba de humo de los 3 flujos end to end contra el API desplegado.
# Solo necesita curl y python3.
#
# Uso: ./scripts/prueba_flujos.sh [correo_municipio] [clave_municipio]
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API="$(cd "$RAIZ/infra" && terraform output -raw url_api)"
API="${API%/}"
MUNI_CORREO="${1:-municipio@reportatuciudad.mx}"
MUNI_CLAVE="${2:-Municipio2026!}"
SUFIJO="$RANDOM$RANDOM"

# Extrae un campo del JSON recibido por la entrada estandar: leer_json reporte.reportId
leer_json() {
  python3 -c '
import json, sys
try:
    dato = json.load(sys.stdin)
except Exception:
    sys.exit(1)
for clave in sys.argv[1].split("."):
    dato = dato.get(clave, "") if isinstance(dato, dict) else ""
print(dato if not isinstance(dato, (dict, list)) else json.dumps(dato, ensure_ascii=False))
' "$1" 2>/dev/null || true
}

# Imprime la respuesta en una sola linea, o tal cual si no es JSON.
compacto() {
  python3 -c '
import json, sys
crudo = sys.stdin.read()
try:
    print(json.dumps(json.loads(crudo), ensure_ascii=False))
except Exception:
    print(crudo.strip()[:300])
'
}

# Falla con un mensaje claro en vez de seguir con un valor vacio.
exigir() {
  local valor="$1" descripcion="$2" respuesta="$3"
  if [ -z "$valor" ]; then
    echo
    echo "FALLO: no se obtuvo $descripcion."
    echo "Respuesta del API: $respuesta"
    echo "Revisa los logs en CloudWatch: /aws/lambda/<proyecto>-<ambiente>-<funcion>"
    exit 1
  fi
}

echo "API: $API"

echo "--- Flujo 1: el ciudadano levanta un reporte"
RESP=$(curl -s -X POST "$API/auth/registro" -H 'Content-Type: application/json' \
  -d "{\"nombre\":\"Ciudadano Prueba\",\"email\":\"ciudadano$SUFIJO@ejemplo.com\",\"password\":\"Prueba12345\"}")
TOKEN_A=$(printf '%s' "$RESP" | leer_json token)
exigir "$TOKEN_A" "el token del ciudadano" "$(printf '%s' "$RESP" | compacto)"

RESP=$(curl -s -X POST "$API/reportes" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d '{"titulo":"Bache de prueba","categoria":"Bache","descripcion":"Generado por la prueba automatica","direccion":"Av. Prueba 100","lat":20.6736,"lng":-103.344}')
REPORT_ID=$(printf '%s' "$RESP" | leer_json reporte.reportId)
exigir "$REPORT_ID" "el folio del reporte" "$(printf '%s' "$RESP" | compacto)"
echo "    Reporte creado: $REPORT_ID"

echo "--- Flujo 3 (parte 1): otro ciudadano confirma y comenta"
RESP=$(curl -s -X POST "$API/auth/registro" -H 'Content-Type: application/json' \
  -d "{\"nombre\":\"Vecina Prueba\",\"email\":\"vecina$SUFIJO@ejemplo.com\",\"password\":\"Prueba12345\"}")
TOKEN_B=$(printf '%s' "$RESP" | leer_json token)
exigir "$TOKEN_B" "el token de la segunda ciudadana" "$(printf '%s' "$RESP" | compacto)"

curl -s -X POST "$API/reportes/$REPORT_ID/confirmaciones" -H "Authorization: Bearer $TOKEN_B" \
  -H 'Content-Type: application/json' -d '{}' | compacto
curl -s -X POST "$API/reportes/$REPORT_ID/comentarios" -H "Authorization: Bearer $TOKEN_B" \
  -H 'Content-Type: application/json' -d '{"texto":"Yo tambien paso por ahi todos los dias"}' | compacto

echo "--- Flujo 2: la cuenta municipal atiende y cierra el reporte"
RESP=$(curl -s -X POST "$API/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$MUNI_CORREO\",\"password\":\"$MUNI_CLAVE\"}")
TOKEN_M=$(printf '%s' "$RESP" | leer_json token)
exigir "$TOKEN_M" "el token de la cuenta municipal" "$(printf '%s' "$RESP" | compacto)"

for ESTADO in "En revisión" "Asignado" "En proceso"; do
  curl -s -X PATCH "$API/admin/reportes/$REPORT_ID/estado" -H "Authorization: Bearer $TOKEN_M" \
    -H 'Content-Type: application/json' \
    -d "{\"estado\":\"$ESTADO\",\"respuesta\":\"Avance automatico de prueba\"}" | compacto
done
curl -s -X PATCH "$API/admin/reportes/$REPORT_ID/estado" -H "Authorization: Bearer $TOKEN_M" \
  -H 'Content-Type: application/json' \
  -d '{"estado":"Resuelto","respuesta":"Bache reparado","evidenciaKey":"evidencias/demo.jpg"}' | compacto

echo "--- Flujo 3 (parte 2): el ciudadano valida el cierre"
curl -s -X POST "$API/reportes/$REPORT_ID/validacion" -H "Authorization: Bearer $TOKEN_A" \
  -H 'Content-Type: application/json' -d '{"resuelto":true}' | compacto

echo "--- Resultado final"
curl -s "$API/reportes/$REPORT_ID" | python3 -c '
import json, sys
d = json.load(sys.stdin)
r = d["reporte"]
print(json.dumps({
    "estado": r["estado"],
    "confirmaciones": r["confirmaciones"],
    "comentarios": len(d["comentarios"]),
    "historial": len(d["historial"]),
}, ensure_ascii=False))'

echo "Prueba terminada. Revisa tu correo: SNS debio enviar las notificaciones."
