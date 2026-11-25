variable "proyecto" {
  description = "Nombre corto del proyecto, usado como prefijo de los recursos"
  type        = string
  default     = "reportatuciudad"
}

variable "ambiente" {
  description = "Ambiente a desplegar (dev, demo, prod)"
  type        = string
  default     = "dev"
}

variable "region" {
  description = "Region de AWS"
  type        = string
  default     = "us-east-1"
}

variable "correos_notificacion" {
  description = "Correos suscritos al topico SNS. AWS envia un correo de confirmacion a cada uno."
  type        = list(string)
  default     = []
}

variable "retencion_logs_dias" {
  description = "Dias de retencion de los logs en CloudWatch"
  type        = number
  default     = 14
}

variable "lambda_memoria_mb" {
  description = "Memoria asignada a las funciones Lambda"
  type        = number
  default     = 256
}

variable "lambda_timeout_seg" {
  description = "Tiempo maximo de ejecucion de las funciones Lambda"
  type        = number
  default     = 15
}

variable "rol_lambda_existente" {
  description = <<-DESC
    Nombre de un rol de IAM que ya existe y que usaran las funciones Lambda.
    Se usa en cuentas donde no se permite crear roles, como el AWS Academy
    Learner Lab (ahi el rol se llama "LabRole"). Si se deja vacio, Terraform
    crea sus propios roles con permisos minimos.
  DESC
  type        = string
  default     = ""
}
