terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  # Estado remoto compartido por el equipo.
  # Primero ejecuta `terraform apply` dentro de infra/bootstrap/ para crear el
  # bucket y la tabla de bloqueo, luego descomenta este bloque y corre `terraform init -migrate-state`.
  # backend "s3" {
  #   bucket         = "reportatuciudad-tfstate-<sufijo>"
  #   key            = "dev/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "reportatuciudad-tflock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Proyecto = var.proyecto
      Ambiente = var.ambiente
      Gestion  = "Terraform"
    }
  }
}
