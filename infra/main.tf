data "aws_caller_identity" "actual" {}

locals {
  nombre = "${var.proyecto}-${var.ambiente}"

  # Los buckets llevan el numero de cuenta como sufijo para ser unicos en todo
  # S3 sin depender de un valor aleatorio, porque los crea el script de
  # despliegue y Terraform solo los configura (ver s3.tf).
  bucket_media    = "${local.nombre}-media-${data.aws_caller_identity.actual.account_id}"
  bucket_frontend = "${local.nombre}-web-${data.aws_caller_identity.actual.account_id}"

  # Cuando la cuenta no permite crear roles (AWS Academy), se reutiliza uno existente.
  crear_roles = var.rol_lambda_existente == ""
  rol_lambda_api = (local.crear_roles
    ? one(aws_iam_role.lambda_api[*].arn)
  : "arn:aws:iam::${data.aws_caller_identity.actual.account_id}:role/${var.rol_lambda_existente}")
  rol_lambda_notificador = (local.crear_roles
    ? one(aws_iam_role.lambda_notificador[*].arn)
  : "arn:aws:iam::${data.aws_caller_identity.actual.account_id}:role/${var.rol_lambda_existente}")

  # Variables de entorno comunes a las funciones del API
  entorno_api = {
    TABLA_USUARIOS      = aws_dynamodb_table.usuarios.name
    TABLA_REPORTES      = aws_dynamodb_table.reportes.name
    TABLA_INTERACCIONES = aws_dynamodb_table.interacciones.name
    BUCKET_MEDIA = local.bucket_media
    COLA_EVENTOS = aws_sqs_queue.eventos.url
    SECRETO_JWT  = aws_secretsmanager_secret.app.name
    AMBIENTE     = var.ambiente
  }

  # Funciones que atienden el API HTTP
  funciones_api = {
    auth = {
      handler     = "handler_auth.handler"
      descripcion = "Registro, inicio de sesion y perfil de usuarios"
    }
    reportes = {
      handler     = "handler_reportes.handler"
      descripcion = "Alta y consulta de reportes ciudadanos"
    }
    interacciones = {
      handler     = "handler_interacciones.handler"
      descripcion = "Confirmaciones, comentarios y validacion del cierre"
    }
    admin = {
      handler     = "handler_admin.handler"
      descripcion = "Panel de la cuenta municipal simulada"
    }
  }

  # routeKey del API HTTP -> funcion que la atiende
  rutas = {
    "POST /auth/registro"                     = "auth"
    "POST /auth/login"                        = "auth"
    "GET /auth/perfil"                        = "auth"
    "POST /reportes"                          = "reportes"
    "GET /reportes"                           = "reportes"
    "GET /reportes/{id}"                      = "reportes"
    "POST /reportes/carga"                    = "reportes"
    "POST /reportes/{id}/confirmaciones"      = "interacciones"
    "POST /reportes/{id}/comentarios"         = "interacciones"
    "POST /reportes/{id}/validacion"          = "interacciones"
    "GET /admin/reportes"                     = "admin"
    "PATCH /admin/reportes/{id}/estado"       = "admin"
    "POST /admin/evidencias"                  = "admin"
  }
}
