# ------------------------------------------------------------------------------
# SQS Queue — event messaging (available for future app integration)
# ------------------------------------------------------------------------------
resource "aws_sqs_queue" "main" {
  name                       = "${var.project_name}-events"
  message_retention_seconds  = 86400
  visibility_timeout_seconds = 30
  receive_wait_time_seconds  = 20

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })

  tags = { Name = "${var.project_name}-events" }
}

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.project_name}-events-dlq"
  message_retention_seconds = 604800

  tags = { Name = "${var.project_name}-events-dlq" }
}
