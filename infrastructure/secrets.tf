# ------------------------------------------------------------------------------
# AWS Secrets Manager — sensitive values injected into ECS tasks
# ------------------------------------------------------------------------------

# Database credentials (JSON: {"username":"...","password":"..."})
resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "${var.project_name}/db-credentials"
  recovery_window_in_days = 0

  tags = { Name = "${var.project_name}-db-credentials" }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
  })
}

# Django secret key
resource "aws_secretsmanager_secret" "django_secret_key" {
  name                    = "${var.project_name}/django-secret-key"
  recovery_window_in_days = 0

  tags = { Name = "${var.project_name}-django-secret-key" }
}

resource "random_password" "django_secret_key" {
  length  = 50
  special = true
}

resource "aws_secretsmanager_secret_version" "django_secret_key" {
  secret_id     = aws_secretsmanager_secret.django_secret_key.id
  secret_string = random_password.django_secret_key.result
}

# Stripe publishable key (update via AWS Console or CLI after deploy)
resource "aws_secretsmanager_secret" "stripe_publishable" {
  name                    = "${var.project_name}/stripe-publishable-key"
  recovery_window_in_days = 0

  tags = { Name = "${var.project_name}-stripe-publishable" }
}

resource "aws_secretsmanager_secret_version" "stripe_publishable" {
  secret_id     = aws_secretsmanager_secret.stripe_publishable.id
  secret_string = "pk_test_placeholder"

  lifecycle { ignore_changes = [secret_string] }
}

# Stripe secret key (update via AWS Console or CLI after deploy)
resource "aws_secretsmanager_secret" "stripe_secret" {
  name                    = "${var.project_name}/stripe-secret-key"
  recovery_window_in_days = 0

  tags = { Name = "${var.project_name}-stripe-secret-key" }
}

resource "aws_secretsmanager_secret_version" "stripe_secret" {
  secret_id     = aws_secretsmanager_secret.stripe_secret.id
  secret_string = "sk_test_placeholder"

  lifecycle { ignore_changes = [secret_string] }
}
