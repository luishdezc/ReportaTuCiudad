# ---------------------------------------------------------------------------
# Amazon S3: bucket de fotografias y evidencias.
#
# El bucket NO se crea con el recurso aws_s3_bucket: ese recurso, al leer su
# estado, llama a s3:GetBucketObjectLockConfiguration, y hay cuentas de clase
# (AWS Academy Learner Lab) donde una SCP niega esa llamada y el apply falla.
# Por eso el bucket lo crea scripts/deploy.sh con la CLI —de forma idempotente—
# y Terraform administra toda su configuracion, que si es accesible.
# ---------------------------------------------------------------------------

resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = local.bucket_media
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

# Las fotos de los reportes se muestran en el mapa publico, por eso son de lectura
# publica. La escritura solo ocurre con URLs prefirmadas que emite la Lambda.
resource "aws_s3_bucket_policy" "media_lectura" {
  bucket     = local.bucket_media
  depends_on = [aws_s3_bucket_public_access_block.media]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "LecturaPublicaDeImagenes"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "arn:aws:s3:::${local.bucket_media}/*"
    }]
  })
}

resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = local.bucket_media

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = local.bucket_media

  rule {
    id     = "borrar-cargas-incompletas"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 3
    }
  }
}
