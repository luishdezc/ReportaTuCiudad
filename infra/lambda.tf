# ---------------------------------------------------------------------------
# AWS Lambda: un unico paquete con todos los modulos y un handler por funcion
# ---------------------------------------------------------------------------

data "archive_file" "backend" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/src"
  output_path = "${path.module}/build/backend.zip"
  excludes    = ["__pycache__"]
}

resource "aws_cloudwatch_log_group" "api" {
  for_each          = local.funciones_api
  name              = "/aws/lambda/${local.nombre}-${each.key}"
  retention_in_days = var.retencion_logs_dias
}

resource "aws_lambda_function" "api" {
  for_each = local.funciones_api

  function_name    = "${local.nombre}-${each.key}"
  description      = each.value.descripcion
  role             = local.rol_lambda_api
  handler          = each.value.handler
  runtime          = "python3.12"
  architectures    = ["arm64"]
  filename         = data.archive_file.backend.output_path
  source_code_hash = data.archive_file.backend.output_base64sha256
  memory_size      = var.lambda_memoria_mb
  timeout          = var.lambda_timeout_seg

  environment {
    variables = local.entorno_api
  }

  depends_on = [
    aws_cloudwatch_log_group.api,
    aws_iam_role_policy.lambda_api,
  ]
}

resource "aws_cloudwatch_log_group" "notificador" {
  name              = "/aws/lambda/${local.nombre}-notificador"
  retention_in_days = var.retencion_logs_dias
}

resource "aws_lambda_function" "notificador" {
  function_name    = "${local.nombre}-notificador"
  description      = "Consume los eventos de SQS y publica las notificaciones en SNS"
  role             = local.rol_lambda_notificador
  handler          = "handler_notificador.handler"
  runtime          = "python3.12"
  architectures    = ["arm64"]
  filename         = data.archive_file.backend.output_path
  source_code_hash = data.archive_file.backend.output_base64sha256
  memory_size      = 128
  timeout          = var.lambda_timeout_seg

  environment {
    variables = {
      TOPICO_SNS   = aws_sns_topic.notificaciones.arn
      URL_FRONTEND = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.notificador,
    aws_iam_role_policy.lambda_notificador,
  ]
}
