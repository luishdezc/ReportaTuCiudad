#!/usr/bin/env bash
# Borra recursos de un intento anterior que impiden volver a desplegar.
#
# En el Learner Lab es comun que un apply falle a medias: los recursos quedan
# creados en AWS pero fuera del estado de Terraform, y el siguiente intento
# falla con "already exists". Este script borra esos restos por nombre.
#
# Uso: ./scripts/limpiar_lab.sh [proyecto-ambiente]   (por defecto: reportatuciudad-dev)
set -euo pipefail

PREFIJO="${1:-reportatuciudad-dev}"

echo "Se borraran los recursos de '$PREFIJO' que hayan quedado de intentos anteriores:"
echo "  - grupos de logs de CloudWatch"
echo "  - el secreto de Secrets Manager"
echo "  - tablas de DynamoDB y buckets de S3 huerfanos (solo si confirmas cada uno)"
read -r -p "Escribe 'limpiar' para continuar: " respuesta
[ "$respuesta" = "limpiar" ] || { echo "Cancelado."; exit 1; }

# --- grupos de logs ---------------------------------------------------------
for grupo in "/aws/apigateway/${PREFIJO}" \
             "/aws/lambda/${PREFIJO}-auth" \
             "/aws/lambda/${PREFIJO}-reportes" \
             "/aws/lambda/${PREFIJO}-interacciones" \
             "/aws/lambda/${PREFIJO}-admin" \
             "/aws/lambda/${PREFIJO}-notificador"; do
  if aws logs delete-log-group --log-group-name "$grupo" 2>/dev/null; then
    echo "  borrado: $grupo"
  fi
done

# --- secreto ----------------------------------------------------------------
if aws secretsmanager delete-secret \
     --secret-id "${PREFIJO}-app-secrets" \
     --force-delete-without-recovery >/dev/null 2>&1; then
  echo "  borrado: secreto ${PREFIJO}-app-secrets"
fi

# --- tablas de DynamoDB huerfanas (del diseno de tres tablas) ---------------
for tabla in "${PREFIJO}-usuarios" "${PREFIJO}-reportes" "${PREFIJO}-interacciones"; do
  if aws dynamodb describe-table --table-name "$tabla" >/dev/null 2>&1; then
    read -r -p "  Borrar la tabla $tabla y sus datos? [s/N] " r
    [ "$r" = "s" ] && aws dynamodb delete-table --table-name "$tabla" >/dev/null && echo "    borrada"
  fi
done

# --- buckets huerfanos ------------------------------------------------------
# Se excluyen los del despliegue actual, que terminan con el numero de cuenta.
CUENTA="$(aws sts get-caller-identity --query Account --output text)"
aws s3api list-buckets \
  --query "Buckets[?starts_with(Name, '${PREFIJO}-') && !ends_with(Name, '${CUENTA}')].Name" \
  --output text \
  | tr '\t' '\n' | while read -r bucket; do
  [ -n "$bucket" ] || continue
  read -r -p "  Borrar el bucket $bucket y su contenido? [s/N] " r < /dev/tty
  if [ "$r" = "s" ]; then
    aws s3 rm "s3://$bucket" --recursive >/dev/null
    aws s3api delete-bucket --bucket "$bucket"
    echo "    borrado"
  fi
done

echo
echo "Listo. Ahora puedes volver a correr: ./scripts/deploy.sh lab"
