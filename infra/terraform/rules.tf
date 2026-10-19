resource "aws_cloudwatch_event_rule" "auth_to_profile" {
  name           = "${var.project}-${var.environment}-auth-to-profile"
  description    = "Enruta eventos de Authentication a la cola de Profile."
  event_bus_name = data.aws_cloudwatch_event_bus.kenko.name
  event_pattern = jsonencode({
    source        = [var.auth_event_source]
    "detail-type" = var.auth_event_detail_types
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "profile_authentication_queue" {
  rule           = aws_cloudwatch_event_rule.auth_to_profile.name
  event_bus_name = data.aws_cloudwatch_event_bus.kenko.name
  target_id      = "profile-authentication-queue"
  arn            = aws_sqs_queue.profile_authentication.arn

  # EventBridge debe tener permiso en la cola antes de asociar el target.
  depends_on = [aws_sqs_queue_policy.allow_eventbridge_to_profile_queue]
}
