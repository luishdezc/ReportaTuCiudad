# ---------------------------------------------------------------------------
# Amazon CloudWatch: metricas de aplicacion, alarmas y dashboard.
#
# Las metricas propias de la aplicacion las publican las Lambdas con el formato
# EMF (una linea de JSON por evento), asi que no cuestan una llamada de red.
# Viven en el espacio de nombres "ReportaTuCiudad":
#
#   ReportesCreados            cuantos problemas reporta la ciudadania
#   ReportesResueltos          cuantos cierra el municipio con evidencia
#   MinutosHastaResolucion     cuanto tarda un reporte desde que nace
#   ConfirmacionesRegistradas  cuanta gente respalda los reportes
#   ComentariosPublicados      cuanta conversacion hay alrededor
#   ReportesReabiertos         cuantos cierres rechazo la comunidad
# ---------------------------------------------------------------------------

locals {
  espacio_app = "ReportaTuCiudad"
  dim_app     = { Ambiente = var.ambiente }
}

# =========================================================== alarmas de negocio

# Un reporte que se cierra y la comunidad reabre es un cierre mal hecho. Que
# pase una vez es ruido; que pase tres veces en una hora es un patron.
resource "aws_cloudwatch_metric_alarm" "reaperturas" {
  alarm_name          = "${local.nombre}-reaperturas"
  alarm_description   = "La comunidad reabrio varios reportes que el municipio dio por resueltos"
  namespace           = local.espacio_app
  metric_name         = "ReportesReabiertos"
  dimensions          = local.dim_app
  statistic           = "Sum"
  period              = 3600
  evaluation_periods  = 1
  threshold           = 3
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.notificaciones.arn]
}

# Si el promedio de resolucion se va arriba de tres dias, hay rezago en la
# bandeja aunque el sistema este sano.
resource "aws_cloudwatch_metric_alarm" "resolucion_lenta" {
  alarm_name          = "${local.nombre}-resolucion-lenta"
  alarm_description   = "El tiempo promedio de resolucion supera los tres dias"
  namespace           = local.espacio_app
  metric_name         = "MinutosHastaResolucion"
  dimensions          = local.dim_app
  statistic           = "Average"
  period              = 3600
  evaluation_periods  = 1
  threshold           = 4320 # 3 dias en minutos
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.notificaciones.arn]
}

# ====================================================== alarmas de plataforma

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

resource "aws_cloudwatch_metric_alarm" "latencia_api" {
  alarm_name          = "${local.nombre}-api-lenta"
  alarm_description   = "El percentil 95 de latencia del API supera los 3 segundos"
  namespace           = "AWS/ApiGateway"
  metric_name         = "Latency"
  extended_statistic  = "p95"
  period              = 300
  evaluation_periods  = 2
  threshold           = 3000
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.notificaciones.arn]

  dimensions = {
    ApiId = aws_apigatewayv2_api.http.id
  }
}

# =================================================================== dashboard

resource "aws_cloudwatch_dashboard" "principal" {
  dashboard_name = "${local.nombre}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      # ---------------------------------------------- estado de la ciudad
      {
        type = "text", x = 0, y = 0, width = 24, height = 1,
        properties = {
          markdown = "## Estado de la ciudad — que esta pasando con los reportes"
        }
      },
      {
        type = "metric", x = 0, y = 1, width = 8, height = 6,
        properties = {
          title  = "Reportes creados y resueltos"
          region = var.region
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          metrics = [
            [local.espacio_app, "ReportesCreados", "Ambiente", var.ambiente, { label = "Creados" }],
            [".", "ReportesResueltos", ".", ".", { label = "Resueltos" }],
          ]
        }
      },
      {
        type = "metric", x = 8, y = 1, width = 8, height = 6,
        properties = {
          title  = "Horas hasta resolver un reporte"
          region = var.region
          view   = "timeSeries"
          period = 3600
          yAxis  = { left = { label = "minutos", showUnits = false } }
          metrics = [
            [local.espacio_app, "MinutosHastaResolucion", "Ambiente", var.ambiente, { stat = "Average", label = "Promedio" }],
            ["...", { stat = "p90", label = "p90" }],
            ["...", { stat = "Maximum", label = "El mas lento" }],
          ]
          annotations = {
            horizontal = [{ label = "Objetivo: 3 dias", value = 4320 }]
          }
        }
      },
      {
        type = "metric", x = 16, y = 1, width = 8, height = 6,
        properties = {
          title  = "Participacion de la comunidad"
          region = var.region
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          metrics = [
            [local.espacio_app, "ConfirmacionesRegistradas", "Ambiente", var.ambiente, { label = "Confirmaciones" }],
            [".", "ComentariosPublicados", ".", ".", { label = "Comentarios" }],
          ]
        }
      },
      {
        type = "metric", x = 0, y = 7, width = 8, height = 6,
        properties = {
          title  = "Reportes por categoria"
          region = var.region
          view   = "bar"
          stat   = "Sum"
          period = 86400
          metrics = [
            for categoria in local.categorias :
            [local.espacio_app, "ReportesCreados", "Ambiente", var.ambiente, "Categoria", categoria, { label = categoria }]
          ]
        }
      },
      {
        type = "metric", x = 8, y = 7, width = 8, height = 6,
        properties = {
          title  = "Cierres rechazados por la comunidad"
          region = var.region
          view   = "singleValue"
          stat   = "Sum"
          period = 86400
          metrics = [
            [local.espacio_app, "ReportesReabiertos", "Ambiente", var.ambiente, { label = "Reportes reabiertos hoy" }],
          ]
        }
      },
      {
        type = "metric", x = 16, y = 7, width = 8, height = 6,
        properties = {
          title  = "Avisos enviados"
          region = var.region
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          metrics = [
            [local.espacio_app, "NotificacionesEnviadas", "Ambiente", var.ambiente, { label = "Entregados" }],
            [".", "NotificacionesFallidas", ".", ".", { label = "Fallidos" }],
          ]
        }
      },

      # ------------------------------------------------ salud de la plataforma
      {
        type = "text", x = 0, y = 13, width = 24, height = 1,
        properties = {
          markdown = "## Salud de la plataforma"
        }
      },
      {
        type = "metric", x = 0, y = 14, width = 12, height = 6,
        properties = {
          title  = "Peticiones y errores del API"
          region = var.region
          view   = "timeSeries"
          stat   = "Sum"
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiId", aws_apigatewayv2_api.http.id, { label = "Peticiones" }],
            [".", "4xx", ".", ".", { label = "Errores 4xx" }],
            [".", "5xx", ".", ".", { label = "Errores 5xx" }],
          ]
        }
      },
      {
        type = "metric", x = 12, y = 14, width = 12, height = 6,
        properties = {
          title  = "Latencia del API"
          region = var.region
          view   = "timeSeries"
          metrics = [
            ["AWS/ApiGateway", "Latency", "ApiId", aws_apigatewayv2_api.http.id, { stat = "Average", label = "Promedio" }],
            ["...", { stat = "p95", label = "p95" }],
          ]
        }
      },
      {
        type = "metric", x = 0, y = 20, width = 12, height = 6,
        properties = {
          title  = "Invocaciones por funcion Lambda"
          region = var.region
          view   = "timeSeries"
          stat   = "Sum"
          metrics = [
            for k, v in local.funciones_api :
            ["AWS/Lambda", "Invocations", "FunctionName", "${local.nombre}-${k}", { label = k }]
          ]
        }
      },
      {
        type = "metric", x = 12, y = 20, width = 12, height = 6,
        properties = {
          title  = "Cola de eventos y notificaciones"
          region = var.region
          view   = "timeSeries"
          metrics = [
            ["AWS/SQS", "NumberOfMessagesSent", "QueueName", aws_sqs_queue.eventos.name, { stat = "Sum", label = "Eventos encolados" }],
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", aws_sqs_queue.eventos_dlq.name, { stat = "Maximum", label = "En la cola de fallidos" }],
            ["AWS/SNS", "NumberOfMessagesPublished", "TopicName", aws_sns_topic.notificaciones.name, { stat = "Sum", label = "Correos publicados" }],
          ]
        }
      },
      {
        type = "log", x = 0, y = 26, width = 24, height = 6,
        properties = {
          title  = "Ultimos errores registrados en el API de reportes"
          region = var.region
          query  = "SOURCE '/aws/lambda/${local.nombre}-reportes' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20"
        }
      },
    ]
  })
}
