# Contrato del API

Base: el output `url_api` de Terraform (`https://<id>.execute-api.<region>.amazonaws.com`).
Autenticación: cabecera `Authorization: Bearer <token>` con el JWT que devuelve el login.
Todas las respuestas son JSON en UTF-8.

## Usuarios y sesión — Lambda `auth`

| Método | Ruta | Sesión | Descripción |
|---|---|---|---|
| POST | `/auth/registro` | — | Crea una cuenta ciudadana. Cuerpo: `nombre`, `email`, `password`, `colonia`. Devuelve `token` y `usuario`. |
| POST | `/auth/login` | — | Inicia sesión. Cuerpo: `email`, `password`. |
| GET | `/auth/perfil` | sí | Datos del usuario en sesión. |

## Reportes — Lambda `reportes`

| Método | Ruta | Sesión | Descripción |
|---|---|---|---|
| POST | `/reportes/carga` | sí | Devuelve una URL prefirmada de S3 para subir la foto (`contentType`). |
| POST | `/reportes` | sí | Crea el reporte: `titulo`, `categoria`, `descripcion`, `direccion`, `lat`, `lng`, `fotoKey`. Estado inicial `Reportado`. |
| GET | `/reportes` | — | Lista pública para el mapa. Filtros: `?estado=`, `?categoria=`, `?limite=`, `?mios=1`. |
| GET | `/reportes/{id}` | — | Detalle con comentarios, historial de estados y lista de confirmadores. |

## Participación ciudadana — Lambda `interacciones`

| Método | Ruta | Sesión | Descripción |
|---|---|---|---|
| POST | `/reportes/{id}/confirmaciones` | sí | "Yo también lo vi". Una por usuario (409 si repite). |
| POST | `/reportes/{id}/comentarios` | sí | Comentario en el reporte (`texto`). |
| POST | `/reportes/{id}/validacion` | sí | Valida el cierre (`resuelto: true|false`). Con 2 o más respuestas negativas mayoritarias el reporte se reabre en `En revisión`. |

## Panel municipal — Lambda `admin` (rol `municipio`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/admin/reportes` | Bandeja ordenada por confirmaciones, con resumen por estado. Filtros `?estado=`, `?categoria=`. |
| PATCH | `/admin/reportes/{id}/estado` | Cambia el estado (`estado`, `respuesta`, `evidenciaKey`). Para `Resuelto` la evidencia es obligatoria. |
| POST | `/admin/evidencias` | URL prefirmada para subir la evidencia de la solución. |

## Códigos de error

`400` datos inválidos · `401` sin sesión o token vencido · `403` la cuenta no es municipal ·
`404` reporte inexistente · `409` confirmación o validación duplicada · `500` error interno (queda en CloudWatch).

## Eventos internos (SQS → SNS)

| Evento | Se emite cuando | Destinatarios |
|---|---|---|
| `reporte.creado` | El ciudadano levanta el reporte | Autor |
| `reporte.estado` | El municipio cambia el estado | Autor + quienes confirmaron |
| `reporte.reabierto` | La comunidad indica que no se resolvió | Autor |