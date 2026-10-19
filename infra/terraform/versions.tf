terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Estado local por ahora. Para usar un backend remoto, configurar primero el bucket.
  # backend "s3" {
  #   bucket       = "REEMPLAZAR-CON-BUCKET-DE-STATE"
  #   key          = "kenko/profile/terraform.tfstate"
  #   region       = "us-east-1"
  #   encrypt      = true
  #   use_lockfile = true
  # }
}

provider "aws" {
  region = var.aws_region
}
