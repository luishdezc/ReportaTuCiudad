# Pruebas unitarias

82 pruebas sobre las seis funciones Lambda, con **pytest** y **moto**. Moto levanta en memoria versiones simuladas de DynamoDB, S3, SQS, SNS y Secrets Manager, así que la suite corre sin credenciales de AWS y sin costo.

## Correrlas

```bash
pip install -r backend/requirements-dev.txt
cd backend
pytest                                   # las 82 pruebas
pytest --cov=src --cov-report=term-missing   # con cobertura por archivo
pytest tests/test_admin.py -v            # un solo archivo
pytest -k "confirmar"                    # las que coincidan con un nombre
```

## Qué cubre cada archivo

| Archivo | Pruebas | Qué verifica |
|---|---|---|
| `test_auth.py` | 13 | Registro, correo duplicado, contraseña corta, login, token alterado, perfil sin sesión |
| `test_reportes.py` | 12 | Alta con validaciones, mapa público, filtros por estado y categoría, detalle, URL prefirmada |
| `test_interacciones.py` | 12 | Confirmación única, comentarios, comentario oficial, validación del cierre y reapertura automática |
| `test_admin.py` | 13 | Permisos del rol municipal, orden por confirmaciones, recorrido completo de estados, evidencia obligatoria |
| `test_notificador.py` | 9 | Formato del asunto y el cuerpo, evidencia opcional, reintento parcial del lote |
| `test_social.py` | 23 | Perfiles e insignias, seguir reportes, feed de la ciudad, estadísticas, avisos en la app y las métricas EMF |

Cobertura actual: **94 %** del código de `backend/src/`. El CI falla si baja del 85 %.

## Cómo está montado

`tests/conftest.py` levanta el entorno simulado **antes** de importar los módulos del backend, porque `common.py` crea sus clientes y sus tablas al importarse. Define también:

- `evento(route_key, cuerpo, token, ruta, consulta)` — arma un evento de API Gateway HTTP API (formato 2.0), que es lo que recibe cada handler.
- `cuerpo(respuesta)` — devuelve el JSON de la respuesta.
- `tablas_limpias` — fixture automática que vacía las tres tablas entre pruebas, para que ninguna dependa de otra.
- `ciudadano`, `municipio`, `reporte` — fixtures que siembran los datos típicos.

Una prueba se ve así:

```python
def test_no_se_puede_confirmar_dos_veces(reporte, ciudadano):
    _, datos = reporte
    vecina = ciudadano("vecina2@ejemplo.com")
    ev = evento("POST /reportes/{id}/confirmaciones", {},
                token=vecina["token"], ruta={"id": datos["reportId"]})
    assert handler_interacciones.handler(ev, None)["statusCode"] == 200
    assert handler_interacciones.handler(ev, None)["statusCode"] == 409
```

## Un error que encontraron las pruebas

`test_recorrer_todos_los_estados` lleva un reporte por los cinco estados y espera cinco entradas en el historial. Fallaba con una sola.

La causa: la llave de orden de los ítems de historial era `HIST#<fecha>` con precisión de segundos. Cuatro cambios de estado dentro del mismo segundo compartían llave, y cada uno sobrescribía al anterior en DynamoDB. En producción pasa menos seguido, pero la reapertura automática escribe su entrada de historial en el mismo segundo que la validación que la dispara, así que era un caso real.

La corrección es `common.ahora_preciso()`, que agrega microsegundos a la marca de tiempo de esos ítems. Las otras interacciones no estaban afectadas: las confirmaciones y los votos llevan el `userId` en la llave, y los comentarios ya traían un identificador aleatorio.

## Lo que no cubren

- **La infraestructura.** `terraform validate` revisa sintaxis y referencias, no que el despliegue funcione. Eso lo verifica `scripts/prueba_flujos.sh` contra el ambiente real.
- **El frontend.** No hay pruebas automatizadas de las interfaces; se revisan a mano con `prueba_flujos.sh` y el navegador.
- **Concurrencia.** Moto no reproduce el bloqueo por ítem de DynamoDB y no es seguro entre hilos, así que las pruebas en paralelo fallarían por el simulador, no por el código. Las escrituras condicionales sí se prueban, de forma secuencial.
