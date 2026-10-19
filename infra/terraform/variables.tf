variable "project" {
  description = "Prefijo común de los recursos de Kenko."
  type        = string
  default     = "kenko"
}

variable "environment" {
  description = "Entorno que se despliega."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment debe ser dev o prod."
  }
}

variable "aws_region" {
  description = "Región AWS para los recursos de Profile."
  type        = string
  default     = "us-east-1"
}

variable "auth_event_source" {
  description = "Source de EventBridge para los eventos de Authentication."
  type        = string
  default     = "kenko.auth"
}

variable "auth_event_detail_types" {
  description = "Detail-types de Authentication que consumirán las colas de Profile."
  type        = list(string)
  default     = ["UserRegistered"]

  validation {
    condition     = length(var.auth_event_detail_types) > 0
    error_message = "Debe configurarse al menos un detail-type de Authentication."
  }
}

variable "max_receive_count" {
  description = "Intentos de procesamiento antes de mover el mensaje a la DLQ."
  type        = number
  default     = 3
}

variable "visibility_timeout_seconds" {
  description = "Tiempo durante el que un mensaje recibido queda invisible."
  type        = number
  default     = 30
}

variable "profile_queue_retention_seconds" {
  description = "Retención de mensajes de la cola principal (4 días)."
  type        = number
  default     = 345600
}

variable "dlq_retention_seconds" {
  description = "Retención de mensajes de la DLQ (14 días)."
  type        = number
  default     = 1209600
}
