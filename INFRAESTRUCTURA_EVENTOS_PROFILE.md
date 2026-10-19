# Infraestructura de eventos de Profile

## Qué se hizo

Se aplicó Terraform para crear en `us-east-1` la infraestructura que recibe eventos de Authentication:

| Recurso | Nombre | Función |
|---|---|---|
| Bus EventBridge | `kenko-dev-bus` | Ya existía; Terraform solo lo referencia. |
| Regla EventBridge | `kenko-dev-auth-to-profile` | Filtra `source=kenko.auth` y `detail-type=UserRegistered`. |
| Cola SQS principal | `kenko-dev-profile-authentication` | Recibe los eventos que coinciden con la regla. |
| DLQ | `kenko-dev-profile-authentication-dlq` | Recibe mensajes tras 3 intentos fallidos. |
| Target | `profile-authentication-queue` | Conecta la regla con la cola principal. |
| Queue policy | — | Permite `sqs:SendMessage` solo a EventBridge desde la regla de Profile. |

Las colas usan SSE-SQS. La principal conserva mensajes 4 días y la DLQ 14 días; el visibility timeout
de la cola principal es 30 segundos. EventBridge entrega el **evento completo**, sin transformar el
cuerpo del mensaje. Terraform no creó el bus ni permisos IAM para que el Worker lea la cola.

## Qué falta

- Implementar/configurar el Worker para recibir mensajes de la cola, extraer `detail.data`, guardar el
  perfil y borrar el mensaje solo después de procesarlo correctamente. No se modificó código de la app.
- Dar al rol donde se ejecute Profile permisos `sqs:ReceiveMessage`, `sqs:DeleteMessage` y
  `sqs:GetQueueAttributes` sobre la cola principal.
- Confirmar con Authentication el contrato definitivo de `UserRegistered` y probar el flujo completo.
- Si se compartirá el estado de Terraform entre desarrolladores, configurar un backend remoto; por ahora
  el state es local en `infra/terraform/terraform.tfstate`.

Esta infraestructura solo cubre el consumo. No crea publicación de eventos de Profile, Outbox ni Relay.

## Comprobaciones y pruebas

### Revisar Terraform y los outputs

```bash
cd infra/terraform
terraform plan
terraform output
```

Después del apply, `terraform plan` debería indicar que no hay cambios pendientes. Para obtener la URL de
la cola:

```bash
QUEUE_URL=$(terraform output -raw profile_authentication_queue_url)
echo "$QUEUE_URL"
```

### Revisar la regla y su target en AWS

```bash
aws events describe-rule \
  --name kenko-dev-auth-to-profile \
  --event-bus-name kenko-dev-bus \
  --region us-east-1

aws events list-targets-by-rule \
  --rule kenko-dev-auth-to-profile \
  --event-bus-name kenko-dev-bus \
  --region us-east-1
```

### Probar solo SQS

Pausa el Worker durante esta prueba para que no consuma el mensaje manual. Envíalo y léelo:

```bash
cd infra/terraform
QUEUE_URL=$(terraform output -raw profile_authentication_queue_url)

aws sqs send-message --queue-url "$QUEUE_URL" \
  --message-body '{"test":"manual"}' --region us-east-1

aws sqs receive-message --queue-url "$QUEUE_URL" \
  --wait-time-seconds 10 \
  --query 'Messages[0].[Body,ReceiptHandle]' \
  --output text --region us-east-1
```

La última respuesta muestra el cuerpo y el `ReceiptHandle`. Bórralo después de copiar ese handle:

```bash
aws sqs delete-message --queue-url "$QUEUE_URL" \
  --receipt-handle '<ReceiptHandle>' --region us-east-1
```

### Probar EventBridge → SQS

**No ejecutes esta prueba sin confirmación explícita:** el evento también coincide con la regla
`kenko-dev-auth-to-notifications`; Notifications lo copiará a su cola y su Worker intentará enviar un
correo.

Si se confirma la prueba, usa `aws events put-events` contra `kenko-dev-bus` con `Source=kenko.auth`,
`DetailType=UserRegistered` y un `Detail` con el contrato de Authentication. Luego revisa la cola con los
comandos de la sección anterior. No se ha publicado ningún evento de prueba.
