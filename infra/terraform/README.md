# Infraestructura de consumo de Profile

Terraform crea únicamente los recursos que Profile necesita para consumir `UserRegistered`:

- Regla `kenko-dev-auth-to-profile` en el bus existente `kenko-dev-bus`.
- Cola principal `kenko-dev-profile-authentication` y DLQ `kenko-dev-profile-authentication-dlq`.
- Target de la regla hacia la cola y policy que permite `sqs:SendMessage` solo a EventBridge desde esa regla.
- Cifrado SSE-SQS, retención, visibility timeout y redrive hacia la DLQ.

No crea el bus, roles/policies IAM para que Profile lea la cola, ni infraestructura para publicar eventos.
La regla entrega el evento EventBridge completo, sin transformación de input.

## Requisitos y comandos

Terraform `>= 1.5.0`, AWS CLI con credenciales ya configuradas y acceso de lectura al bus existente.
Los valores por defecto crean el entorno `dev` en `us-east-1`.

```bash
cd infra/terraform
terraform init
terraform fmt -recursive
terraform validate
terraform plan
```

El estado es local. `.terraform/`, los statefiles y los `*.tfvars` locales se excluyen de Git.
Revisa el plan antes de cualquier `apply`; este proyecto no ejecuta `apply` automáticamente.

## Enrutamiento

| Evento | Regla | Cola principal | DLQ |
|---|---|---|---|
| `source=kenko.auth`, `detail-type=UserRegistered` | `kenko-dev-auth-to-profile` | `kenko-dev-profile-authentication` | `kenko-dev-profile-authentication-dlq` |

La lista `auth_event_detail_types` permite agregar tipos de evento Authentication posteriormente.
El consumidor debe esperar el envelope completo de EventBridge (`source`, `detail-type`, `detail`, etc.).
El contrato de `detail` incluye `metadata` y `data`; confirma con Authentication los campos definitivos que
Profile almacenará.

## Verificación después del apply aprobado

Para probar solo SQS, detén temporalmente el Worker para evitar que consuma el mensaje de prueba, y ejecuta
`aws sqs send-message` a la URL de `terraform output -raw profile_authentication_queue_url`; léelo con
`aws sqs receive-message` y bórralo con `aws sqs delete-message` usando su receipt handle.

Para probar la cadena completa, un evento `UserRegistered` publicado en `kenko-dev-bus` también coincide
con la regla `kenko-dev-auth-to-notifications`: Notifications copiará la prueba a su propia cola y su Worker
intentará enviar un correo. **No publiques ese evento de prueba sin confirmación explícita.**
