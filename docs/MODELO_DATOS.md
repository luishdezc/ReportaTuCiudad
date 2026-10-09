# Modelo de datos (DynamoDB)

Tres tablas en modo bajo demanda (`PAY_PER_REQUEST`).

## `*-usuarios`

| Campo | Tipo | Notas |
|---|---|---|
| `userId` (PK) | S | `usr_<hex>` |
| `email` | S | GSI `email-index`, usado en el login |
| `nombre`, `colonia` | S | Perfil |
| `rol` | S | `ciudadano` o `municipio` |
| `passwordHash` | S | PBKDF2-SHA256, 120 000 iteraciones, formato `salt$hash` |
| `creadoEn` | S | ISO-8601 |

## `*-reportes`

| Campo | Tipo | Notas |
|---|---|---|
| `reportId` (PK) | S | `rep_<hex>`, es el folio que ve el ciudadano |
| `estado` | S | GSI `estado-index` (PK) — `Reportado`, `En revisión`, `Asignado`, `En proceso`, `Resuelto` |
| `creadoEn` | S | GSI `estado-index` (SK): permite ordenar por fecha dentro de cada estado |
| `titulo`, `categoria`, `descripcion`, `direccion` | S | Contenido del reporte |
| `lat`, `lng` | S | Coordenadas guardadas como texto para evitar pérdida de precisión |
| `fotoKey`, `evidenciaKey` | S | Llaves de los objetos en el bucket de media |
| `autorId`, `autorNombre`, `autorEmail` | S | Quién reportó |
| `confirmaciones`, `comentarios` | N | Contadores actualizados con `UpdateExpression` atómico |
| `validacionesSi`, `validacionesNo` | N | Respuestas al cierre |
| `respuestaMunicipal` | S | Último mensaje de la cuenta municipal |
| `actualizadoEn` | S | ISO-8601 |

## `*-interacciones`

Tabla de una sola entidad con clave compuesta: todo lo que cuelga de un reporte se lee con un `Query`.

| `reportId` (PK) | `sk` (SK) | Contenido |
|---|---|---|
| `rep_...` | `CONF#<userId>` | Confirmación ("yo también lo vi"). La condición `attribute_not_exists(sk)` impide duplicados. |
| `rep_...` | `COM#<fecha>#<id>` | Comentario: `texto`, `autorNombre`, `oficial` |
| `rep_...` | `VAL#<userId>` | Validación del cierre: `resuelto` |
| `rep_...` | `HIST#<fecha>` | Historial de estados: `estado`, `mensaje`, `autor` |

## Por qué este diseño

- El mapa consulta `GET /reportes` una sola vez y el detalle hace un `Query` único por `reportId`.
- La bandeja municipal filtra por estado con el GSI, sin escanear toda la tabla.
- Los contadores viven en el reporte para no contar filas en cada carga del mapa.
- La clave compuesta `sk` permite agregar tipos nuevos de interacción sin crear tablas.