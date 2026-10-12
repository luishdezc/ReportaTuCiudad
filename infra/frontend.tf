# ---------------------------------------------------------------------------
# Sitio estatico del frontend alojado en Amazon S3.
# El bucket lo crea scripts/deploy.sh con la CLI; aqui solo se configura
# (ver la nota en s3.tf).
# ---------------------------------------------------------------------------

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = local.bucket_frontend

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = local.bucket_frontend
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket     = local.bucket_frontend
  depends_on = [aws_s3_bucket_public_access_block.frontend]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "LecturaPublicaDelSitio"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "arn:aws:s3:::${local.bucket_frontend}/*"
    }]
  })
}

locals {
  ruta_frontend = "${path.module}/../frontend"

  archivos_frontend = toset(concat(
    tolist(fileset(local.ruta_frontend, "**/*.html")),
    tolist(fileset(local.ruta_frontend, "**/*.js")),
    tolist(fileset(local.ruta_frontend, "**/*.css")),
    tolist(fileset(local.ruta_frontend, "**/*.svg")),
  ))

  tipos_mime = {
    html = "text/html; charset=utf-8"
    js   = "application/javascript; charset=utf-8"
    css  = "text/css; charset=utf-8"
    svg  = "image/svg+xml"
    png  = "image/png"
    ico  = "image/x-icon"
  }
}

resource "aws_s3_object" "frontend" {
  for_each = local.archivos_frontend

  bucket       = local.bucket_frontend
  key          = each.value
  source       = "${local.ruta_frontend}/${each.value}"
  etag         = filemd5("${local.ruta_frontend}/${each.value}")
  content_type = lookup(local.tipos_mime, element(split(".", each.value), length(split(".", each.value)) - 1), "application/octet-stream")
}

# Configuracion que el navegador lee para saber a que API llamar
resource "aws_s3_object" "configuracion" {
  bucket       = local.bucket_frontend
  key          = "js/config.js"
  content_type = "application/javascript; charset=utf-8"

  content = <<-JS
    // Archivo generado por Terraform. No editar a mano.
    window.CONFIG = {
      API_URL: "${aws_apigatewayv2_stage.default.invoke_url}",
      AMBIENTE: "${var.ambiente}"
    };
  JS
}
