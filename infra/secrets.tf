# ---------------------------------------------------------------------------
# AWS Secrets Manager: llave con la que se firman los tokens de sesion (JWT)
# ---------------------------------------------------------------------------

resource "random_password" "jwt" {
  length  = 48
  special = false
}

resource "aws_secretsmanager_secret" "app" {
  name                    = "${local.nombre}-app-secrets"
  description             = "Secretos de la aplicacion ReportaTuCiudad"
  recovery_window_in_days = 0 # prototipo escolar: permite recrear el secreto sin esperar
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    jwt_secret = random_password.jwt.result
  })
}
