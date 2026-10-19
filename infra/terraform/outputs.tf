output "profile_authentication_queue_url" {
  description = "URL de la cola principal de eventos de Authentication para Profile."
  value       = aws_sqs_queue.profile_authentication.url
}

output "profile_authentication_queue_arn" {
  description = "ARN de la cola principal de eventos de Authentication para Profile."
  value       = aws_sqs_queue.profile_authentication.arn
}

output "profile_authentication_dlq_url" {
  description = "URL de la dead-letter queue de Profile."
  value       = aws_sqs_queue.profile_authentication_dlq.url
}

output "profile_authentication_dlq_arn" {
  description = "ARN de la dead-letter queue de Profile."
  value       = aws_sqs_queue.profile_authentication_dlq.arn
}

output "auth_to_profile_rule_arn" {
  description = "ARN de la regla que enruta eventos de Authentication hacia Profile."
  value       = aws_cloudwatch_event_rule.auth_to_profile.arn
}
