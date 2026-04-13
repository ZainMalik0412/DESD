# ------------------------------------------------------------------------------
# ECS Cluster
# ------------------------------------------------------------------------------
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ------------------------------------------------------------------------------
# CloudWatch Log Group
# ------------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 30
}

# ------------------------------------------------------------------------------
# ECS Task Definition
# ------------------------------------------------------------------------------
resource "aws_ecs_task_definition" "web" {
  family                   = "${var.project_name}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "web"
    image = "${aws_ecr_repository.web.repository_url}:latest"

    portMappings = [{
      containerPort = var.container_port
      protocol      = "tcp"
    }]

    environment = [
      { name = "DATABASE_ENGINE", value = "mysql" },
      { name = "DATABASE_HOST", value = aws_db_instance.main.address },
      { name = "DATABASE_PORT", value = "3306" },
      { name = "DATABASE_NAME", value = var.db_name },
      { name = "DJANGO_DEBUG", value = "False" },
      { name = "DJANGO_ALLOWED_HOSTS", value = "${var.domain_name},www.${var.domain_name}" },
      { name = "REDIS_URL", value = "redis://${aws_elasticache_cluster.main.cache_nodes[0].address}:6379/0" },
      { name = "SQS_QUEUE_URL", value = aws_sqs_queue.main.url },
    ]

    secrets = [
      { name = "DATABASE_USER", valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:username::" },
      { name = "DATABASE_PASSWORD", valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:password::" },
      { name = "DJANGO_SECRET_KEY", valueFrom = aws_secretsmanager_secret.django_secret_key.arn },
      { name = "STRIPE_PUBLISHABLE_KEY", valueFrom = aws_secretsmanager_secret.stripe_publishable.arn },
      { name = "STRIPE_SECRET_KEY", valueFrom = aws_secretsmanager_secret.stripe_secret.arn },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/${var.project_name}"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "web"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:${var.container_port}/health/')\""]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 120
    }
  }])
}

# ------------------------------------------------------------------------------
# ECS Service — rolling deploy with circuit breaker rollback
# ------------------------------------------------------------------------------
resource "aws_ecs_service" "web" {
  name            = "${var.project_name}-web"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 180

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = var.container_port
  }

  # CI/CD updates the task definition; don't let Terraform revert it
  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  depends_on = [aws_lb_listener.https]
}
