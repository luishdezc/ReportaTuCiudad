# Modelo de datos (DynamoDB)

Cinco tablas en modo bajo demanda (`PAY_PER_REQUEST`).

## `*-usuarios`

| Campo | Tipo | Notas |
|---|---|---|
| `userId` (PK) | S | `usr_<hex>` |
| `email` | S | GSI `email-index`, usado en el login |
| `nombre`, `colonia` | S | Perfil |
| `rol` | S | `ciudadano` o `municipio` |
| `confirmacionesDadas`, `comentariosEscritos` | N | Contadores del perfil, con sumas atómicas |
| `passwordHash` | S | PBKDF2-SHA256, 120 000 iteraciones, formato `salt$hash` |
| `creadoEn` | S | ISO-8601 |

## `*-reportes`

| Campo | Tipo | Notas |
|---|---|---|
| `reportId` (PK) | S | `rep_<hex>`, es el folio que ve el ciudadano |
| `estado` | S | GSI `estado-index` (PK) — `Reportado`, `En revisión`, `Asignado`, `En proceso`, `Resuelto` |
| `autorId` | S | GSI `autor-index` (PK) — los reportes de un ciudadano en su perfil, con una sola consulta |
| `creadoEn` | S | GSI `estado-index` (SK): permite ordenar por fecha dentro de cada estado |
| `titulo`, `categoria`, `descripcion`, `direccion` | S | Contenido del reporte |
| `lat`, `lng` | S | Coordenadas guardadas como texto para evitar pérdida de precisión |
| `fotoKey`, `evidenciaKey` | S | Llaves de los objetos en el bucket de media |
| `autorId`, `autorNombre`, `autorEmail` | S | Quién reportó |
| `autorColonia` | S | Colonia del autor al momento de reportar |
| `confirmaciones`, `comentarios`, `seguidores` | N | Contadores actualizados con `UpdateExpression` atómico |
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
| `rep_...` | `SEG#<userId>` | Seguidor del reporte, para recibir sus avisos |

## `*-notificaciones`

Los avisos dentro de la aplicación, uno por usuario y evento.

| Campo | Tipo | Notas |
|---|---|---|
| `userId` (PK) | S | A quién va dirigido |
| `sk` (SK) | S | `NOT#<fecha>#<id>`: devuelve del más nuevo al más viejo con `ScanIndexForward=false` |
| `tipo` | S | `confirmacion`, `comentario`, `estado` o `reapertura` |
| `titulo`, `cuerpo`, `reportId` | S | Contenido del aviso y a qué reporte lleva |
| `leida` | BOOL | La campana cuenta los que siguen en `false` |
| `expiraEn` | N | TTL a 60 días: los avisos viejos se borran solos |

## `*-actividad`

El muro público de la ciudad y los contadores globales, en la misma tabla.

| `dia` (PK) | `sk` (SK) | Contenido |
|---|---|---|
| `2026-11-14` | `<fecha>#<id>` | Un evento del feed: `tipo`, `reportId`, `titulo`, `categoria`, `estado`, `actor`, `detalle` |
| `TOTALES` | `GLOBAL` | Contadores de la ciudad: `reportesCreados`, `reportesResueltos`, `confirmaciones`, `comentarios`, `reabiertos`, `minutosResolucionAcumulados` y uno por categoría |

La partición por día no es cosmética. Con una sola partición para toda la ciudad, cada reporte nuevo escribiría en la misma y se toparía con el límite por partición de DynamoDB. Partiendo por fecha, el feed se arma consultando los últimos tres días: tres consultas en vez de un escaneo. Los contadores sí viven en una partición fija, pero son sumas atómicas sobre un único ítem, que es justo para lo que DynamoDB las ofrece. Los eventos caducan solos a los 30 días con TTL.

## Por qué este diseño

- El mapa consulta `GET /reportes` una sola vez y el detalle hace un `Query` único por `reportId`.
- La bandeja municipal filtra por estado con el GSI, sin escanear toda la tabla.
- Los contadores viven en el reporte para no contar filas en cada carga del mapa.
- La clave compuesta `sk` permite agregar tipos nuevos de interacción sin crear tablas: los seguidores entraron como `SEG#<userId>` sin tocar el esquema.
- El perfil de un ciudadano sale del índice `autor-index` con una consulta, en lugar de escanear la tabla y filtrar en memoria.
- Las dos tablas nuevas usan TTL, así que no crecen sin límite ni hay que programar una limpieza.
