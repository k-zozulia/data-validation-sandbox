terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "eu-central-1"
}

locals {
  project = "dvs"
  tags = {
    Project = "data-validation-sandbox"
    Managed = "terraform"
  }
}

resource "aws_ecr_repository" "backend" {
  name                 = "${local.project}-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true 

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = local.tags
}

output "ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}