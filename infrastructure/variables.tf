variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "brfnapp"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "brfnapp.com"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "brfn_db"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "brfn_user"
}

variable "container_port" {
  description = "Port the Django app listens on"
  type        = number
  default     = 8000
}

variable "cpu" {
  description = "Fargate task CPU units (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Fargate task memory in MiB"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Number of ECS tasks to run"
  type        = number
  default     = 2
}

variable "github_org" {
  description = "GitHub organization or username"
  type        = string
  default     = "ZainMalik0412"
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "DESD"
}
