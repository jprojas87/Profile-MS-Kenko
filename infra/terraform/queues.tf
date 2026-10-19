locals {
  common_tags = {
    Project     = var.project
    Environment = var.environment
    Service     = "profile"
    ManagedBy   = "terraform"
  }
}

resource "aws_sqs_queue" "profile_authentication_dlq" {
  name                      = "${var.project}-${var.environment}-profile-authentication-dlq"
  message_retention_seconds = var.dlq_retention_seconds
  sqs_managed_sse_enabled   = true

  tags = local.common_tags
}

resource "aws_sqs_queue" "profile_authentication" {
  name                       = "${var.project}-${var.environment}-profile-authentication"
  visibility_timeout_seconds = var.visibility_timeout_seconds
  message_retention_seconds  = var.profile_queue_retention_seconds
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.profile_authentication_dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = local.common_tags
}

data "aws_iam_policy_document" "allow_eventbridge_to_profile_queue" {
  statement {
    sid       = "AllowEventBridgeFromProfileAuthenticationRule"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.profile_authentication.arn]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.auth_to_profile.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "allow_eventbridge_to_profile_queue" {
  queue_url = aws_sqs_queue.profile_authentication.id
  policy    = data.aws_iam_policy_document.allow_eventbridge_to_profile_queue.json
}
