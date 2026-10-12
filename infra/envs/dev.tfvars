proyecto = "reportatuciudad"
ambiente = "dev"
region   = "us-east-1"

# Correos que recibiran las notificaciones del prototipo.
# AWS envia un correo de confirmacion a cada direccion: hay que aceptarlo.
correos_notificacion = [
  "integrante1@ejemplo.com",
  "integrante2@ejemplo.com",
  "integrante3@ejemplo.com",
]

retencion_logs_dias = 14
lambda_memoria_mb   = 256
lambda_timeout_seg  = 15
