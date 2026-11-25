#!/usr/bin/env bash
# Elimina toda la infraestructura del ambiente para no consumir creditos.
# Uso: ./scripts/destroy.sh [ambiente]
set -euo pipefail

AMBIENTE="${1:-dev}"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ/infra"

echo "Se eliminaran TODOS los recursos del ambiente '$AMBIENTE' (incluidos los datos)."
read -r -p "Escribe 'destruir' para continuar: " respuesta
[ "$respuesta" = "destruir" ] || { echo "Cancelado."; exit 1; }

BUCKET_WEB="$(terraform output -raw bucket_frontend 2>/dev/null || true)"
BUCKET_MEDIA="$(terraform output -raw bucket_media 2>/dev/null || true)"

terraform destroy -input=false -auto-approve -var-file="envs/${AMBIENTE}.tfvars"

# Los buckets los crea deploy.sh con la CLI, asi que Terraform no los borra.
for bucket in "$BUCKET_WEB" "$BUCKET_MEDIA"; do
  if [ -n "$bucket" ] && aws s3api head-bucket --bucket "$bucket" >/dev/null 2>&1; then
    aws s3 rm "s3://$bucket" --recursive >/dev/null
    aws s3api delete-bucket --bucket "$bucket"
    echo "Bucket eliminado: $bucket"
  fi
done

echo "Recursos eliminados."
