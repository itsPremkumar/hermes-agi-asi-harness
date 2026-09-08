# Aetheria Infrastructure as Code — AWS
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket = "aetheria-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "us-east-1"
}

variable "cluster_name" {
  default = "aetheria-prod"
}

# EKS Cluster
module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  cluster_name    = var.cluster_name
  cluster_version = "1.29"
  subnet_ids      = module.vpc.private_subnets

  eks_managed_node_groups = {
    main = {
      desired_size = 3
      max_size     = 10
      min_size     = 2
      instance_types = ["m5.xlarge"]
    }
  }
}

# VPC
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  name    = "aetheria-vpc"
  cidr    = "10.0.0.0/16"
  azs     = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

# RDS PostgreSQL for memory persistence
resource "aws_db_instance" "memory" {
  identifier     = "aetheria-memory"
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t3.medium"
  allocated_storage = 100
  db_name        = "aetheria"
  username       = "hermes"
  password       = var.db_password
  skip_final_snapshot = true
}

variable "db_password {
  sensitive = true
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}
