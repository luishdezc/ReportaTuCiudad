#!/usr/bin/env bash
# Despliega la infraestructura y la aplicacion completa.
# Uso: ./scripts/deploy.sh [ambiente]   (por defecto: dev; usa "lab" en AWS Academy)
set -euo pipefail

AMBIENTE="${1:-dev}"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TFVARS="$RAIZ/infra/envs/${AMBIENTE}.tfvars"
cd "$RAIZ/infra"

[ -f "$TFVARS" ] || { echo "No existe $TFVARS"; exit 1; }

# Lee un valor sencillo (clave = "valor") del archivo de variables.
leer_var() {
  local clave="$1" predeterminado="${2:-}" valor
  valor="$(sed -n "s/^[[:space:]]*${clave}[[:space:]]*=[[:space:]]*\"\([^\"]*\)\".*/\1/p" "$TFVARS" | head -1)"
  echo "${valor:-$predeterminado}"
}

PROYECTO="$(leer_var proyecto reportatuciudad)"
AMB="$(leer_var ambiente dev)"
REGION="$(leer_var region us-east-1)"
CUENTA="$(aws sts get-caller-identity --query Account --output text)"

BUCKET_WEB="${PROYECTO}-${AMB}-web-${CUENTA}"
BUCKET_MEDIA="${PROYECTO}-${AMB}-media-${CUENTA}"

# Los buckets se crean aqui y no con el recurso aws_s3_bucket: ese recurso lee
# la configuracion de Object Lock, y hay cuentas de clase donde una SCP niega
# esa llamada. Terraform administra toda la demas configuracion del bucket.
crear_bucket() {
  local nombre="$1"
  if aws s3api head-bucket --bucket "$nombre" --region "$REGION" >/dev/null 2>&1; then
    echo "    ya existe: $nombre"
  elif [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$nombre" --region "$REGION" >/dev/null
    echo "    creado:    $nombre"
  else
    aws s3api create-bucket --bucket "$nombre" --region "$REGION" \
      --create-bucket-configuration "LocationConstraint=$REGION" >/dev/null
    echo "    creado:    $nombre"
  fi
}

echo "==> 1/5 Preparando los buckets de S3"
crear_bucket "$BUCKET_WEB"
crear_bucket "$BUCKET_MEDIA"

echo "==> 2/5 Inicializando Terraform"
terraform init -input=false

echo "==> 3/5 Validando la configuracion"
terraform fmt -check -recursive || echo "    (aviso: hay archivos sin formatear, corre 'terraform fmt -recursive')"
terraform validate

echo "==> 4/5 Aplicando la infraestructura del ambiente '$AMBIENTE'"
terraform apply -input=false -auto-approve -var-file="envs/${AMBIENTE}.tfvars"

echo "==> 5/5 Sincronizando el frontend con S3"
aws s3 sync "$RAIZ/frontend" "s3://$(terraform output -raw bucket_frontend)" \
  --exclude "js/config.js" \
  --delete \
  --cache-control "max-age=60"

echo
echo "Despliegue terminado:"
echo "  Sitio web : $(terraform output -raw url_sitio)"
echo "  API       : $(terraform output -raw url_api)"
echo "  Dashboard : $(terraform output -raw dashboard)"
echo
echo "Recuerda confirmar la suscripcion de SNS en el correo que envia AWS."
