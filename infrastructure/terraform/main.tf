# ============================================================
# Terraform - Infrastructure as Code
# ============================================================
# Hermes AGI/ASI Harness - CI/CD Pipeline Infrastructure
# ============================================================

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.31"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }

  backend "s3" {
    bucket         = "hermes-agi-asi-harness-tfstate"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "hermes-agi-asi-harness"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ============================================================
# Variables
# ============================================================

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "staging"

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be staging or production."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.29"
}

variable "node_instance_type" {
  description = "EC2 instance type for worker nodes"
  type        = string
  default     = "t3.large"
}

variable "desired_capacity" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 3
}

variable "min_capacity" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 2
}

variable "max_capacity" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 10
}

# ============================================================
# Data Sources
# ============================================================

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

data "aws_ecr_repository" "app" {
  name = "hermes-agi-asi-harness"
}

# ============================================================
# VPC
# ============================================================

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "hermes-${var.environment}-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "hermes-${var.environment}-igw"
  }
}

resource "aws_subnet" "public" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  map_public_ip_on_launch = true

  tags = {
    Name = "hermes-${var.environment}-public-${count.index + 1}"
    "kubernetes.io/role/elb" = "1"
  }
}

resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "hermes-${var.environment}-private-${count.index + 1}"
    "kubernetes.io/role/internal-elb" = "1"
  }
}

resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "hermes-${var.environment}-nat-eip"
  }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name = "hermes-${var.environment}-nat"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "hermes-${var.environment}-public-rt"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = {
    Name = "hermes-${var.environment}-private-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = 3
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = 3
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# ============================================================
# EKS Cluster
# ============================================================

resource "aws_eks_cluster" "main" {
  name     = "hermes-${var.environment}"
  role_arn = aws_iam_role.cluster.arn
  version  = var.cluster_version

  vpc_config {
    subnet_ids              = aws_subnet.private[*].id
    endpoint_private_access = true
  }

  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  depends_on = [
    aws_iam_role_policy_attachment.cluster_policy,
    aws_iam_role_policy_attachment.service_policy,
  ]
}

resource "aws_kms_key" "eks" {
  description             = "EKS Secret Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name = "hermes-${var.environment}-eks-key"
  }
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "hermes-${var.environment}-nodes"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = aws_subnet.private[*].id

  instance_types = [var.node_instance_type]

  scaling_config {
    desired_size = var.desired_capacity
    min_size     = var.min_capacity
    max_size     = var.max_capacity
  }

  update_config {
    max_unavailable_percentage = 25
  }

  labels = {
    environment = var.environment
    role        = "worker"
  }

  depends_on = [
    aws_iam_role_policy_attachment.node_policy,
    aws_iam_role_policy_attachment.cni_policy,
    aws_iam_role_policy_attachment.ecr_policy,
  ]

  tags = {
    Name = "hermes-${var.environment}-nodes"
  }
}

# ============================================================
# IAM Roles
# ============================================================

resource "aws_iam_role" "cluster" {
  name = "hermes-${var.environment}-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.cluster.name
}

resource "aws_iam_role_policy_attachment" "service_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSServicePolicy"
  role       = aws_iam_role.cluster.name
}

resource "aws_iam_role" "node" {
  name = "hermes-${var.environment}-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.node.name
}

resource "aws_iam_role_policy_attachment" "cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.node.name
}

resource "aws_iam_role_policy_attachment" "ecr_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.node.name
}

# ============================================================
# RDS (PostgreSQL)
# ============================================================

resource "aws_db_subnet_group" "main" {
  name       = "hermes-${var.environment}-db-subnet"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "hermes-${var.environment}-db-subnet"
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "hermes-${var.environment}-rds-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  tags = {
    Name = "hermes-${var.environment}-rds-sg"
  }
}

resource "aws_db_instance" "main" {
  identifier     = "hermes-${var.environment}-db"
  engine         = "postgres"
  engine_version = "16.1"
  instance_class = var.environment == "production" ? "db.r6g.large" : "db.t3.medium"

  allocated_storage     = 100
  max_allocated_storage = 500
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "hermes_${var.environment}"
  username = "hermes_admin"
  password = random_password.db_password.result

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = var.environment == "production" ? 30 : 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  performance_insights_enabled = true

  deletion_protection = var.environment == "production"
  skip_final_snapshot = var.environment != "production"

  tags = {
    Name = "hermes-${var.environment}-db"
  }
}

resource "random_password" "db_password" {
  length  = 32
  special = false
}

# ============================================================
# ElastiCache (Redis)
# ============================================================

resource "aws_elasticache_subnet_group" "main" {
  name       = "hermes-${var.environment}-cache-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_security_group" "redis" {
  name_prefix = "hermes-${var.environment}-redis-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  tags = {
    Name = "hermes-${var.environment}-redis-sg"
  }
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "hermes-${var.environment}"
  description          = "Redis cluster for Hermes ${var.environment}"

  node_type            = var.environment == "production" ? "cache.r6g.large" : "cache.t3.medium"
  num_cache_clusters   = var.environment == "production" ? 3 : 2

  engine               = "redis"
  engine_version       = "7.1"

  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis_auth.result

  automatic_failover_enabled = var.environment == "production"

  tags = {
    Name = "hermes-${var.environment}-redis"
  }
}

resource "random_password" "redis_auth" {
  length  = 32
  special = false
}

# ============================================================
# Monitoring & Alerting
# ============================================================

resource "aws_cloudwatch_dashboard" "pipeline" {
  dashboard_name = "hermes-${var.environment}-pipeline"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Pipeline Success Rate"
          metrics = [
            ["Hermes/Pipeline", "Success", "Environment", var.environment],
            [".", "Failure", ".", "."]
          ]
          view   = "timeSeries"
          region = var.aws_region
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Deployment Duration"
          metrics = [
            ["Hermes/Pipeline", "DeployDuration", "Environment", var.environment]
          ]
          view   = "timeSeries"
          region = var.aws_region
          period = 300
          stat   = "Average"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "Node CPU Utilization"
          metrics = [
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", aws_eks_node_group.main.id]
          ]
          view   = "timeSeries"
          region = var.aws_region
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "Database Connections"
          metrics = [
            ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", aws_db_instance.main.identifier]
          ]
          view   = "timeSeries"
          region = var.aws_region
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "Redis Memory Usage"
          metrics = [
            ["AWS/ElastiCache", "DatabaseMemoryUsagePercentage", "ReplicationGroupId", aws_elasticache_replication_group.main.id]
          ]
          view   = "timeSeries"
          region = var.aws_region
          period = 300
        }
      }
    ]
  })
}

resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "hermes-${var.environment}-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "5xxErrorRate"
  namespace           = "Hermes/Application"
  period              = 300
  statistic           = "Average"
  threshold           = 5
  alarm_description   = "High 5xx error rate detected in ${var.environment}"
  alarm_actions       = [aws_sns_topic.alerts.insns[0].arn]

  dimensions = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "pipeline_failure" {
  alarm_name          = "hermes-${var.environment}-pipeline-failure"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "PipelineFailure"
  namespace           = "Hermes/Pipeline"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Pipeline failure detected in ${var.environment}"
  alarm_actions       = [aws_sns_topic.alerts.insns[0].arn]
}

resource "aws_sns_topic" "alerts" {
  name = "hermes-${var.environment}-alerts"

  tags = {
    Name = "hermes-${var.environment}-alerts"
  }
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = "devops@hermes-agi-asi-harness.dev"
}

resource "aws_sns_topic_subscription" "slack" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "https"
  endpoint  = "https://hooks.slack.com/services/xxx/yyy/zzz"
}

# ============================================================
# Outputs
# ============================================================

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "db_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.main.endpoint
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "db_password_secret" {
  description = "DB password (stored in random_password)"
  value       = random_password.db_password.result
  sensitive   = true
}

output "redis_auth_secret" {
  description = "Redis auth token"
  value       = random_password.redis_auth.result
  sensitive   = true
}
