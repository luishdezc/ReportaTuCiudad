#!/usr/bin/env bash
# Crea reportes de ejemplo repartidos en el mapa y en distintos estados, para que
# la demostracion no empiece con el mapa vacio. Solo necesita curl y python3.
#
# Uso: ./scripts/sembrar_demo.sh [correo_municipio] [clave_municipio]
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API="$(cd "$RAIZ/infra" && terraform output -raw url_api)"
API="${API%/}"
MUNI_CORREO="${1:-municipio@reportatuciudad.mx}"
MUNI_CLAVE="${2:-Municipio2026!}"
SUFIJO="$RANDOM$RANDOM"

leer_json() {
  python3 -c '
import json, sys
try:
    dato = json.load(sys.stdin)
except Exception:
    sys.exit(1)
for clave in sys.argv[1].split("."):
    dato = dato.get(clave, "") if isinstance(dato, dict) else ""
print(dato if not isinstance(dato, (dict, list)) else "")
' "$1" 2>/dev/null || true
}

exigir() {
  [ -n "$1" ] || { echo "FALLO: no se obtuvo $2."; echo "Respuesta: $3"; exit 1; }
}

registrar() {
  local nombre="$1" correo="$2" resp
  resp=$(curl -s -X POST "$API/auth/registro" -H 'Content-Type: application/json' \
    -d "{\"nombre\":\"$nombre\",\"email\":\"$correo\",\"password\":\"Demo12345\"}")
  local t; t=$(printf '%s' "$resp" | leer_json token)
  exigir "$t" "el token de $nombre" "$resp"
  echo "$t"
}

crear_reporte() {  # token titulo categoria descripcion direccion lat lng
  local resp
  resp=$(curl -s -X POST "$API/reportes" -H "Authorization: Bearer $1" \
    -H 'Content-Type: application/json' \
    -d "{\"titulo\":\"$2\",\"categoria\":\"$3\",\"descripcion\":\"$4\",\"direccion\":\"$5\",\"lat\":$6,\"lng\":$7}")
  local id; id=$(printf '%s' "$resp" | leer_json reporte.reportId)
  exigir "$id" "el folio de \"$2\"" "$resp"
  echo "$id"
}

estado() {  # token_municipio reportId estado respuesta [evidenciaKey]
  local cuerpo="{\"estado\":\"$3\",\"respuesta\":\"$4\""
  [ -n "${5:-}" ] && cuerpo="$cuerpo,\"evidenciaKey\":\"$5\""
  cuerpo="$cuerpo}"
  curl -s -o /dev/null -X PATCH "$API/admin/reportes/$2/estado" \
    -H "Authorization: Bearer $1" -H 'Content-Type: application/json' -d "$cuerpo"
}

echo "Sembrando datos de demostracion en $API"

TOKEN_A=$(registrar "Ana Vecina"    "ana$SUFIJO@ejemplo.com")
TOKEN_B=$(registrar "Beto Peatón"   "beto$SUFIJO@ejemplo.com")
TOKEN_C=$(registrar "Carmen Colonia" "carmen$SUFIJO@ejemplo.com")

R1=$(crear_reporte "$TOKEN_A" "Bache profundo sobre Av. Hidalgo" "Bache" \
  "Bache de medio metro que ya ponchó dos llantas esta semana." "Av. Hidalgo 240" 20.6760 -103.3470)
R2=$(crear_reporte "$TOKEN_B" "Luminaria apagada en el parque" "Luminaria dañada" \
  "La lámpara de la esquina lleva tres semanas sin encender." "Parque Rojo, lado norte" 20.6680 -103.3580)
R3=$(crear_reporte "$TOKEN_C" "Basura acumulada en la banqueta" "Acumulación de basura" \
  "Se junta basura cada fin de semana y nadie la recoge." "Calle Morelos 115" 20.6820 -103.3400)
R4=$(crear_reporte "$TOKEN_A" "Fuga de agua en la esquina" "Fuga de agua" \
  "Sale agua limpia de la banqueta desde hace cuatro días." "Juárez esq. Colón" 20.6710 -103.3300)
R5=$(crear_reporte "$TOKEN_B" "Semáforo intermitente" "Semáforo dañado" \
  "El semáforo quedó en amarillo intermitente y es un cruce muy transitado." "Av. Vallarta y Chapultepec" 20.6900 -103.3520)
echo "  5 reportes creados"

# Confirmaciones y comentarios: dan prioridad y llenan la bandeja del municipio
for par in "$TOKEN_B:$R1" "$TOKEN_C:$R1" "$TOKEN_A:$R3" "$TOKEN_C:$R5"; do
  curl -s -o /dev/null -X POST "$API/reportes/${par#*:}/confirmaciones" \
    -H "Authorization: Bearer ${par%%:*}" -H 'Content-Type: application/json' -d '{}'
done
curl -s -o /dev/null -X POST "$API/reportes/$R1/comentarios" -H "Authorization: Bearer $TOKEN_C" \
  -H 'Content-Type: application/json' -d '{"texto":"Yo paso por ahí todos los días, ya está peor."}'
curl -s -o /dev/null -X POST "$API/reportes/$R3/comentarios" -H "Authorization: Bearer $TOKEN_B" \
  -H 'Content-Type: application/json' -d '{"texto":"El camión no pasa desde hace dos semanas."}'
echo "  4 confirmaciones y 2 comentarios"

# Estados variados para que la bandeja y el mapa no se vean todos iguales
RESP=$(curl -s -X POST "$API/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$MUNI_CORREO\",\"password\":\"$MUNI_CLAVE\"}")
TOKEN_M=$(printf '%s' "$RESP" | leer_json token)
exigir "$TOKEN_M" "el token de la cuenta municipal" "$RESP"

estado "$TOKEN_M" "$R3" "En revisión" "Turnado a Servicios Públicos para su valoración."
estado "$TOKEN_M" "$R5" "Asignado"    "Cuadrilla de semáforos asignada."
estado "$TOKEN_M" "$R4" "En proceso"  "Personal en sitio reparando la fuga."
estado "$TOKEN_M" "$R2" "Resuelto"    "Luminaria sustituida." "evidencias/demo.jpg"
echo "  estados variados aplicados (quedan 1 Reportado, 1 En revisión, 1 Asignado, 1 En proceso, 1 Resuelto)"

echo
echo "Listo. El mapa ya tiene reportes repartidos y la bandeja municipal tiene de todo."
echo "El reporte \"$R1\" quedó en Reportado con 2 confirmaciones: úsalo si quieres atenderlo en vivo."
