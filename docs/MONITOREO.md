# Monitoreo

Todo se define en `infra/monitoring.tf` y se crea con Terraform: seis métricas propias de la aplicación, diez alarmas y un dashboard.

## Las seis métricas de aplicación

Viven en el espacio de nombres **`ReportaTuCiudad`** y las publican las funciones Lambda con **EMF** (Embedded Metric Format): la función imprime una línea de JSON y CloudWatch la convierte en métrica. Así no hace falta llamar a `PutMetricData`, que costaría una petición de red por cada evento y sumaría latencia a la respuesta del usuario.

| Métrica | Qué responde | Dónde se publica |
|---|---|---|
| `ReportesCreados` | Cuántos problemas reporta la ciudadanía, y de qué tipo | `handler_reportes.crear` |
| `ReportesResueltos` | Cuántos cierra el municipio con evidencia | `handler_admin.cambiar_estado` |
| `MinutosHastaResolucion` | Cuánto tarda un reporte desde que nace hasta que se cierra | `handler_admin.cambiar_estado` |
| `ConfirmacionesRegistradas` | Cuánta gente respalda los reportes de otros | `handler_interacciones.confirmar` |
| `ComentariosPublicados` | Cuánta conversación hay alrededor | `handler_interacciones.comentar` |
| `ReportesReabiertos` | Cuántos cierres rechazó la comunidad | `handler_interacciones.validar_solucion` |

Cada llamada emite **dos juegos de dimensiones**: uno por `Ambiente`, para el total, y otro que agrega `Categoria` donde aplica. Así el dashboard puede graficar el total y el desglose sin instrumentar dos veces.

`handler_notificador` publica además `NotificacionesEnviadas` y `NotificacionesFallidas`.

## Las diez alarmas

Todas avisan al mismo tópico de SNS, el que ya recibe las notificaciones del equipo.

**Dos miden el negocio, no la infraestructura:**

| Alarma | Se dispara cuando | Por qué importa |
|---|---|---|
| `reaperturas` | La comunidad reabre 3 o más cierres en una hora | El municipio está cerrando reportes sin arreglar el problema. El sistema está sano; el proceso no |
| `resolucion-lenta` | El promedio de resolución pasa de 4320 minutos (3 días) | Hay rezago en la bandeja aunque nada haya fallado |

**Ocho miden la plataforma:**

| Alarma | Se dispara cuando |
|---|---|
| `<funcion>-errores` (una por cada una de las seis Lambdas) | La función devuelve algún error en 5 minutos |
| `api-5xx` | El API devuelve 3 o más errores 5xx en 5 minutos |
| `api-lenta` | El percentil 95 de latencia pasa de 3 segundos en dos periodos seguidos |
| `notificaciones-dlq` | Hay mensajes en la cola de mensajes muertos, es decir, un aviso no se pudo entregar |

## El dashboard

Se abre con la URL que imprime `terraform output -raw dashboard`, o en **CloudWatch → Paneles → `reportatuciudad-dev-dashboard`**.

Está partido en dos bloques, y el orden es deliberado: primero lo que le importa a un funcionario, después lo que le importa a quien opera el sistema.

**Estado de la ciudad**

1. Reportes creados contra resueltos, en el tiempo.
2. Horas hasta resolver: promedio, p90 y el peor caso, con una línea marcando el objetivo de tres días.
3. Participación: confirmaciones y comentarios.
4. Reportes por categoría, en barras.
5. Cierres rechazados por la comunidad, como número grande.
6. Avisos entregados contra fallidos.

**Salud de la plataforma**

7. Peticiones y errores del API.
8. Latencia promedio y p95.
9. Invocaciones por función Lambda.
10. Cola de eventos, cola de fallidos y correos publicados.
11. Los últimos errores de la Lambda de reportes, en texto.

## Verificarlo antes de presentar

```bash
cd infra && terraform output -raw dashboard     # la URL del dashboard
aws cloudwatch describe-alarms \
  --query 'MetricAlarms[?starts_with(AlarmName, `reportatuciudad`)].[AlarmName,StateValue]' \
  --output table
```

**Las métricas EMF tardan unos minutos** en aparecer: CloudWatch tiene que procesar los logs antes de convertirlos en métricas. Corre `scripts/sembrar_demo.sh` al menos diez minutos antes de la presentación o el dashboard saldrá en ceros.

Para disparar una alarma en vivo y enseñar que funciona, lo más rápido es forzar el estado desde la CLI:

```bash
aws cloudwatch set-alarm-state \
  --alarm-name reportatuciudad-dev-reaperturas \
  --state-value ALARM \
  --state-reason "Demostración en clase"
```

Llega el correo en segundos y la alarma regresa sola a `OK` en la siguiente evaluación. Conviene decir que fue forzada: es una demostración del camino de la alerta, no un incidente real.
