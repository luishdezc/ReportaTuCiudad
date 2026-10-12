# Guía de despliegue

Todo el prototipo se levanta con Terraform. No se crea ningún recurso a mano desde la consola.

## 1. Requisitos

| Herramienta | Versión mínima | Comprobación |
|---|---|---|
| Terraform | 1.6 | `terraform version` |
| AWS CLI | 2.x | `aws --version` |
| Python | 3.12 (para los scripts locales) | `python3 --version` |
| (sin dependencias extra: los scripts solo usan curl y python3) | | |

Credenciales de AWS configuradas con un perfil que pueda crear Lambda, API Gateway, DynamoDB, S3, SQS, SNS, IAM, Secrets Manager y CloudWatch:

```bash
aws configure            # o: export AWS_PROFILE=escuela
aws sts get-caller-identity
```

## 2. Estado remoto (una sola vez por equipo)

```bash
cd infra/bootstrap
terraform init
terraform apply          # crea el bucket de estado y la tabla de bloqueo
```

Copia los outputs, descomenta el bloque `backend "s3"` en `infra/versions.tf` con el nombre del bucket y ejecuta:

```bash
cd ../
terraform init -migrate-state
```

> Si solo quieres probar en tu máquina puedes saltarte este paso: Terraform usará estado local.

## 3. Configurar el ambiente

Edita `infra/envs/dev.tfvars` y pon los correos reales del equipo en `correos_notificacion`.
AWS envía un correo de confirmación de la suscripción de SNS: **hay que abrirlo y aceptarlo**,
si no, no llegan las notificaciones.

## 3 bis. Si usas el AWS Academy Learner Lab

La cuenta del laboratorio (rol `voclabs`) tiene dos restricciones que afectan al proyecto, y el repositorio ya viene preparado para las dos:

1. **No se pueden crear roles de IAM** (`iam:CreateRole` denegado). Las Lambdas reutilizan el rol `LabRole` que el laboratorio ya trae. Eso lo activa la variable `rol_lambda_existente`.
2. **Una SCP niega `s3:GetBucketObjectLockConfiguration`.** El recurso `aws_s3_bucket` de Terraform hace esa llamada cada vez que lee el bucket, así que el apply fallaba. Por eso los dos buckets los crea `scripts/deploy.sh` con la CLI, de forma idempotente, y Terraform administra toda su configuración (política, CORS, sitio estático, ciclo de vida y objetos).

Usa el archivo de variables del laboratorio, donde ya está puesto `rol_lambda_existente = "LabRole"`:

```bash
$EDITOR infra/envs/lab.tfvars     # pon tu correo real
./scripts/deploy.sh lab
```

Recuerda que el laboratorio **borra todo al cerrar la sesión**, así que tendrás que volver a desplegar en cada clase. El estado de Terraform local deja de coincidir cuando eso pasa; si el `apply` se queja de recursos que ya no existen, borra `infra/terraform.tfstate*` y vuelve a desplegar.

## 4. Desplegar

```bash
./scripts/deploy.sh dev          # o: ./scripts/deploy.sh lab
```

El script crea los buckets si no existen, hace `terraform init`, `validate`, `apply` y sincroniza el frontend al bucket web.
Al terminar imprime la URL del sitio, la del API y la del dashboard de CloudWatch.

También puedes hacerlo a mano:

```bash
cd infra
terraform init
terraform plan  -var-file=envs/dev.tfvars
terraform apply -var-file=envs/dev.tfvars
```

## 5. Crear la cuenta oficial municipal

El registro público solo crea ciudadanos. La cuenta municipal se siembra una vez:

```bash
./scripts/crear_cuenta_municipal.sh municipio@reportatuciudad.mx "Municipio2026!"
```

Con esa cuenta se entra a `admin.html` (Panel municipal).

## 6. Probar los tres flujos

```bash
./scripts/prueba_flujos.sh municipio@reportatuciudad.mx "Municipio2026!"
```

Recorre el ciclo completo: alta del reporte, confirmación y comentario de otro ciudadano,
avance de estados desde el municipio, cierre con evidencia y validación del ciudadano.
En paralelo deben llegar los correos de SNS.

## 7. Apagar el ambiente

```bash
./scripts/destroy.sh dev
```

Elimina todos los recursos, incluidos los datos de DynamoDB y los objetos de S3
(los buckets están con `force_destroy = true`). Úsalo al terminar cada sesión de trabajo
para no consumir créditos.

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `BucketAlreadyExists` | El sufijo aleatorio chocó con otra cuenta. Corre `terraform apply` de nuevo o cambia `proyecto`. |
| El sitio carga pero el mapa no trae reportes | `js/config.js` no se regeneró: corre `terraform apply` y recarga con Ctrl+F5. |
| No llegan correos | La suscripción de SNS sigue en *Pending confirmation*: revisa la bandeja y acepta. |
| `403` en el panel municipal | Iniciaste sesión con una cuenta ciudadana. Usa la cuenta creada en el paso 5. |
| Error al subir la foto | El navegador bloqueó el PUT a S3: revisa la regla CORS del bucket de media. |
| `terraform destroy` falla por el secreto | El secreto tiene `recovery_window_in_days = 0`; si quedó programado para borrado, espera o cámbiale el nombre. |
| `AccessDenied: iam:CreateRole` | Cuenta de clase sin permiso para crear roles. Despliega con `./scripts/deploy.sh lab`, que usa `LabRole`. |
| `AccessDenied: s3:GetBucketObjectLockConfiguration` con *explicit deny in a service control policy* | Viene de una SCP del laboratorio. Ya está resuelto: los buckets los crea `deploy.sh`, no el recurso `aws_s3_bucket`. Si lo ves, es que estás usando una versión vieja de `infra/`. |
| `BucketAlreadyOwnedByYou` al desplegar otra vez | Normal: el bucket ya existía y el script lo reutiliza. |
| `ResourceAlreadyExistsException` en grupos de logs, o `ResourceExistsException` en el secreto | Quedaron recursos de un `apply` que falló a medias y que ya no están en el estado. Corre `./scripts/limpiar_lab.sh` y vuelve a desplegar. |
