# ---------------------------------------------------------------------------
# AWS IAM: un rol por tipo de funcion, con permisos minimos.
#
# Si la variable rol_lambda_existente trae un nombre (p. ej. "LabRole" en el
# AWS Academy Learner Lab, donde iam:CreateRole esta prohibido), no se crea
# nada de esto y las Lambdas usan ese rol. Ver locals en main.tf.
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "asumir_lambda" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# ------------------------------- rol de las funciones del API --------------
resource "aws_iam_role" "lambda_api" {
  count = local.crear_roles ? 1 : 0

  name               = "${local.nombre}-rol-lambda-api"
  assume_role_policy = data.aws_iam_policy_document.asumir_lambda.json
}

resource "aws_iam_role_policy_attachment" "api_logs" {
  count = local.crear_roles ? 1 : 0

  role       = aws_iam_role.lambda_api[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "lambda_api" {
  statement {
    sid = "TablasDynamoDB"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:TransactWriteItems",
    ]
    resources = [
      aws_dynamodb_table.usuarios.arn,
      "${aws_dynamodb_table.usuarios.arn}/index/*",
      aws_dynamodb_table.reportes.arn,
      "${aws_dynamodb_table.reportes.arn}/index/*",
      aws_dynamodb_table.interacciones.arn,
      "${aws_dynamodb_table.interacciones.arn}/index/*",
    ]
  }

  statement {
    sid       = "ImagenesEnS3"
    actions   = ["s3:PutObject", "s3:GetObject"]
    resources = ["arn:aws:s3:::${local.bucket_media}/*"]
  }

  statement {
    sid       = "EncolarEventos"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.eventos.arn]
  }

  statement {
    sid       = "LeerSecretoDeLaApp"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.app.arn]
  }
}

resource "aws_iam_role_policy" "lambda_api" {
  count = local.crear_roles ? 1 : 0

  name   = "${local.nombre}-politica-lambda-api"
  role   = aws_iam_role.lambda_api[0].id
  policy = data.aws_iam_policy_document.lambda_api.json
}

# ------------------------------- rol del notificador -----------------------
resource "aws_iam_role" "lambda_notificador" {
  count = local.crear_roles ? 1 : 0

  name               = "${local.nombre}-rol-lambda-notificador"
  assume_role_policy = data.aws_iam_policy_document.asumir_lambda.json
}

resource "aws_iam_role_policy_attachment" "notificador_logs" {
  count = local.crear_roles ? 1 : 0

  role       = aws_iam_role.lambda_notificador[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "lambda_notificador" {
  statement {
    sid = "ConsumirCola"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [aws_sqs_queue.eventos.arn]
  }

  statement {
    sid       = "PublicarNotificaciones"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.notificaciones.arn]
  }
}

resource "aws_iam_role_policy" "lambda_notificador" {
  count = local.crear_roles ? 1 : 0

  name   = "${local.nombre}-politica-lambda-notificador"
  role   = aws_iam_role.lambda_notificador[0].id
  policy = data.aws_iam_policy_document.lambda_notificador.json
}
