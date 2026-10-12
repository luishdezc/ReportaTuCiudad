# ---------------------------------------------------------------------------
# Amazon DynamoDB: usuarios, reportes e interacciones (comentarios, confirmaciones,
# validaciones e historial de estados). Ver docs/MODELO_DATOS.md.
#
# La tabla de interacciones usa llave compuesta, asi que todo lo que cuelga de
# un reporte vive en su particion y se lee con una sola Query.
# ---------------------------------------------------------------------------

resource "aws_dynamodb_table" "usuarios" {
  name         = "${local.nombre}-usuarios"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "reportes" {
  name         = "${local.nombre}-reportes"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "reportId"

  attribute {
    name = "reportId"
    type = "S"
  }

  attribute {
    name = "estado"
    type = "S"
  }

  attribute {
    name = "creadoEn"
    type = "S"
  }

  # Permite listar el mapa y la bandeja del municipio por estado,
  # del mas nuevo al mas viejo, sin escanear la tabla.
  global_secondary_index {
    name            = "estado-index"
    hash_key        = "estado"
    range_key       = "creadoEn"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "interacciones" {
  name         = "${local.nombre}-interacciones"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "reportId"
  range_key    = "sk" # CONF#<userId> | COM#<fecha>#<id> | VAL#<userId> | HIST#<fecha>

  attribute {
    name = "reportId"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }
}
