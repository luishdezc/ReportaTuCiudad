# ---------------------------------------------------------------------------
# Amazon CloudWatch: alarmas y dashboard del prototipo
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "errores_lambda" {
  for_each = local.funciones_api

  alarm_name          = "${local.nombre}-${each.key}-errores"
  alarm_description   = "La funcion ${each.key} devolvio errores en los ultimos 5 minutos"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.notificaciones.arn]

  dimensions = {
    FunctionName = aws_lambda_function.api[each.key].function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "errores_api" {
  alarm_name          = "${local.nombre}-api-5xx"
  alarm_description   = "El API devolvio errores 5xx"
  namespace           = "AWS/ApiGateway"
  metric_name         = "5xx"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 3
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.notificaciones.arn]

  dimensions = {
    ApiId = aws_apigatewayv2_api.http.id
  }
}

resource "aws_cloudwatch_metric_alarm" "mensajes_en_dlq" {
  alarm_name          = "${local.nombre}-notificaciones-dlq"
  alarm_description   = "Hay notificaciones que no se pudieron enviar (cola de mensajes muertos)"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.notificaciones.arn]

  dimensions = {
    QueueName = aws_sqs_queue.eventos_dlq.name
  }
}

resource "aws_cloudwatch_dashboard" "principal" {
  dashboard_name = "${local.nombre}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 12, height = 6,
        properties = {
          title  = "Peticiones y errores del API"
          region = var.region
          view   = "timeSeries"
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiId", aws_apigatewayv2_api.http.id, { stat = "Sum", label = "Peticiones" }],
            [".", "4xx", ".", ".", { stat = "Sum", label = "Errores 4xx" }],
            [".", "5xx", ".", ".", { stat = "Sum", label = "Errores 5xx" }],
          ]
        }
      },
      {
        type = "metric", x = 12, y = 0, width = 12, height = 6,
        properties = {
          title  = "Latencia del API (ms)"
          region = var.region
          view   = "timeSeries"
          metrics = [
            ["AWS/ApiGateway", "Latency", "ApiId", aws_apigatewayv2_api.http.id, { stat = "Average", label = "Promedio" }],
            ["...", { stat = "p95", label = "p95" }],
          ]
        }
      },
      {
        type = "metric", x = 0, y = 6, width = 12, height = 6,
        properties = {
          title  = "Invocaciones por funcion Lambda"
          region = var.region
          view   = "timeSeries"
          metrics = [for k, v in local.funciones_api :
            ["AWS/Lambda", "Invocations", "FunctionName", "${local.nombre}-${k}", { stat = "Sum", label = k }]
          ]
        }
      },
      {
        type = "metric", x = 12, y = 6, width = 12, height = 6,
        properties = {
          title  = "Cola de notificaciones (SQS) y envios (SNS)"
          region = var.region
          view   = "timeSeries"
          metrics = [
            ["AWS/SQS", "NumberOfMessagesSent", "QueueName", aws_sqs_queue.eventos.name, { stat = "Sum", label = "Eventos encolados" }],
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", aws_sqs_queue.eventos_dlq.name, { stat = "Maximum", label = "En DLQ" }],
            ["AWS/SNS", "NumberOfMessagesPublished", "TopicName", aws_sns_topic.notificaciones.name, { stat = "Sum", label = "Notificaciones" }],
          ]
        }
      },
      {
        type = "log", x = 0, y = 12, width = 24, height = 6,
        properties = {
          title  = "Ultimos errores registrados en el API de reportes"
          region = var.region
          query  = "SOURCE '/aws/lambda/${local.nombre}-reportes' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20"
        }
      },
    ]
  })
}
