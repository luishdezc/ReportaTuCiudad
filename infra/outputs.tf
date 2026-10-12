output "url_api" {
  description = "URL base del API HTTP"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "url_sitio" {
  description = "URL publica de la aplicacion web"
  value       = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
}

output "bucket_frontend" {
  description = "Bucket del sitio estatico (usado por scripts/deploy.sh)"
  value       = local.bucket_frontend
}

output "bucket_media" {
  description = "Bucket de fotografias y evidencias"
  value       = local.bucket_media
}

output "tabla_usuarios" {
  description = "Tabla de usuarios (usada para crear la cuenta municipal)"
  value       = aws_dynamodb_table.usuarios.name
}

output "topico_notificaciones" {
  description = "ARN del topico SNS de notificaciones"
  value       = aws_sns_topic.notificaciones.arn
}

output "cola_eventos" {
  description = "URL de la cola SQS de eventos"
  value       = aws_sqs_queue.eventos.url
}

output "dashboard" {
  description = "Enlace al dashboard de CloudWatch"
  value       = "https://${var.region}.console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards:name=${aws_cloudwatch_dashboard.principal.dashboard_name}"
}
