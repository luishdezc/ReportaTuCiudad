# ---------------------------------------------------------------------------
# Ambiente para el AWS Academy Learner Lab (rol voclabs).
#
# Esa cuenta no permite crear roles de IAM, asi que las funciones Lambda
# reutilizan el rol "LabRole" que el laboratorio ya trae.
#
#   ./scripts/deploy.sh lab
# ---------------------------------------------------------------------------

proyecto = "reportatuciudad"
ambiente = "dev"
region   = "us-east-1"

rol_lambda_existente = "LabRole"

# Correos que recibiran las notificaciones. AWS manda un correo de confirmacion
# a cada direccion: hay que abrirlo y aceptarlo.
correos_notificacion = [
  "tucorreo@iteso.mx",
]

retencion_logs_dias = 14
lambda_memoria_mb   = 256
lambda_timeout_seg  = 15
