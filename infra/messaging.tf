# ---------------------------------------------------------------------------
# Amazon SQS + Amazon SNS: procesamiento asincrono y notificaciones
# ---------------------------------------------------------------------------

resource "aws_sqs_queue" "eventos_dlq" {
  name                      = "${local.nombre}-eventos-dlq"
  message_retention_seconds = 1209600 # 14 dias
}

resource "aws_sqs_queue" "eventos" {
  name                       = "${local.nombre}-eventos"
  visibility_timeout_seconds = var.lambda_timeout_seg * 6
  message_retention_seconds  = 345600 # 4 dias

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.eventos_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sns_topic" "notificaciones" {
  name = "${local.nombre}-notificaciones"
}

# Cada correo recibe un mensaje de AWS para confirmar la suscripcion.
resource "aws_sns_topic_subscription" "correos" {
  for_each  = toset(var.correos_notificacion)
  topic_arn = aws_sns_topic.notificaciones.arn
  protocol  = "email"
  endpoint  = each.value
}

resource "aws_lambda_event_source_mapping" "cola_a_notificador" {
  event_source_arn                   = aws_sqs_queue.eventos.arn
  function_name                      = aws_lambda_function.notificador.arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 5
  function_response_types            = ["ReportBatchItemFailures"]
}
