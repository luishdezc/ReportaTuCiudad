# ---------------------------------------------------------------------------
# Bootstrap del estado remoto de Terraform.
# Se ejecuta UNA sola vez y por separado del despliegue principal:
#   cd infra/bootstrap && terraform init && terraform apply
# Despues se descomenta el bloque backend "s3" en infra/versions.tf.
# ---------------------------------------------------------------------------

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.60" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

provider "aws" {
  region = var.region
}

resource "random_id" "sufijo" {
  byte_length = 3
}

resource "aws_s3_bucket" "tfstate" {
  bucket = "reportatuciudad-tfstate-${random_id.sufijo.hex}"
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "tflock" {
  name         = "reportatuciudad-tflock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}

output "bucket_estado" {
  value = aws_s3_bucket.tfstate.bucket
}

output "tabla_bloqueo" {
  value = aws_dynamodb_table.tflock.name
}
