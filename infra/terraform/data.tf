data "aws_cloudwatch_event_bus" "kenko" {
  name = "${var.project}-${var.environment}-bus"
}
