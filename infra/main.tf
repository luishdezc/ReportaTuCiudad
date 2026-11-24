data "aws_caller_identity" "actual" {}

locals {
  nombre = "${var.proyecto}-${var.ambiente}"
  cuenta = data.aws_caller_identity.actual.account_id

  # Los buckets llevan el numero de cuenta como sufijo para ser unicos en todo
  # S3 sin depender de un valor aleatorio, porque los crea el script de
  # despliegue y Terraform solo los configura (ver s3.tf).
  bucket_media    = "${local.nombre}-media-${local.cuenta}"
  bucket_frontend = "${local.nombre}-web-${local.cuenta}"

  # Cuando la cuenta no permite crear roles (AWS Academy), se reutiliza uno existente.
  crear_roles   = var.rol_lambda_existente == ""
  rol_existente = "arn:aws:iam::${local.cuenta}:role/${var.rol_lambda_existente}"

  rol_lambda_api         = local.crear_roles ? one(aws_iam_role.lambda_api[*].arn) : local.rol_existente
  rol_lambda_notificador = local.crear_roles ? one(aws_iam_role.lambda_notificador[*].arn) : local.rol_existente

  # Las mismas categorias que valida backend/src/common.py. El dashboard las
  # usa para desglosar los reportes creados.
  categorias = [
    "Bache",
    "Luminaria dañada",
    "Acumulación de basura",
    "Fuga de agua",
    "Árbol caído",
    "Semáforo dañado",
    "Otro",
  ]

  # Variables de entorno comunes a las funciones del API
  entorno_api = {
    TABLA_USUARIOS       = aws_dynamodb_table.usuarios.name
    TABLA_REPORTES       = aws_dynamodb_table.reportes.name
    TABLA_INTERACCIONES  = aws_dynamodb_table.interacciones.name
    TABLA_NOTIFICACIONES = aws_dynamodb_table.notificaciones.name
    TABLA_ACTIVIDAD      = aws_dynamodb_table.actividad.name
    BUCKET_MEDIA         = local.bucket_media
    COLA_EVENTOS         = aws_sqs_queue.eventos.url
    SECRETO_JWT          = aws_secretsmanager_secret.app.name
    AMBIENTE             = var.ambiente
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
    social = {
      handler     = "handler_social.handler"
      descripcion = "Perfiles, feed de la ciudad, estadisticas y avisos"
    }
  }

  # routeKey del API HTTP -> funcion que la atiende
  rutas = {
    "POST /auth/registro"                = "auth"
    "POST /auth/login"                   = "auth"
    "GET /auth/perfil"                   = "auth"
    "POST /reportes"                     = "reportes"
    "GET /reportes"                      = "reportes"
    "GET /reportes/{id}"                 = "reportes"
    "POST /reportes/carga"               = "reportes"
    "POST /reportes/{id}/confirmaciones" = "interacciones"
    "POST /reportes/{id}/comentarios"    = "interacciones"
    "POST /reportes/{id}/validacion"     = "interacciones"
    "POST /reportes/{id}/seguidores"     = "interacciones"
    "DELETE /reportes/{id}/seguidores"   = "interacciones"
    "GET /usuarios/{id}/perfil"          = "social"
    "GET /actividad"                     = "social"
    "GET /estadisticas"                  = "social"
    "GET /notificaciones"                = "social"
    "POST /notificaciones/leidas"        = "social"
    "GET /admin/reportes"                = "admin"
    "PATCH /admin/reportes/{id}/estado"  = "admin"
    "POST /admin/evidencias"             = "admin"
  }
}
