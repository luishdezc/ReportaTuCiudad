# ---------------------------------------------------------------------------
# Amazon API Gateway (HTTP API): punto de entrada unico de la aplicacion
# ---------------------------------------------------------------------------

resource "aws_apigatewayv2_api" "http" {
  name          = "${local.nombre}-api"
  description   = "API de ReportaTuCiudad"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PATCH", "OPTIONS"]
    allow_headers = ["content-type", "authorization"]
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_integration" "api" {
  for_each = local.funciones_api

  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api[each.key].invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = var.lambda_timeout_seg * 1000
}

resource "aws_apigatewayv2_route" "rutas" {
  for_each = local.rutas

  api_id    = aws_apigatewayv2_api.http.id
  route_key = each.key
  target    = "integrations/${aws_apigatewayv2_integration.api[each.value].id}"
}

resource "aws_lambda_permission" "api_gateway" {
  for_each = local.funciones_api

  statement_id  = "PermitirInvocacionDesdeApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

resource "aws_cloudwatch_log_group" "api_acceso" {
  name              = "/aws/apigateway/${local.nombre}"
  retention_in_days = var.retencion_logs_dias
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_acceso.arn
    format = jsonencode({
      requestId  = "$context.requestId"
      ip         = "$context.identity.sourceIp"
      method     = "$context.httpMethod"
      ruta       = "$context.routeKey"
      estado     = "$context.status"
      latenciaMs = "$context.responseLatency"
      error      = "$context.integrationErrorMessage"
    })
  }

  default_route_settings {
    throttling_burst_limit = 50
    throttling_rate_limit  = 100
  }
}
