"""Lambda de participacion ciudadana: confirmaciones, comentarios y validacion del cierre."""
from botocore.exceptions import ClientError

import common as c


def confirmar(evento):
    """'Yo tambien lo vi': evita duplicados y suma prioridad al reporte."""
    sesion = c.usuario_actual(evento)
    report_id = _id(evento)
    reporte = _reporte(report_id)
    if reporte["autorId"] == sesion["sub"]:
        raise c.ErrorHttp(400, "No puedes confirmar tu propio reporte")
    try:
        c.interacciones.put_item(
            Item={
                "reportId": report_id,
                "sk": "CONF#%s" % sesion["sub"],
                "tipo": "confirmacion",
                "userId": sesion["sub"],
                "email": sesion["email"],
                "creadoEn": c.ahora(),
            },
            ConditionExpression="attribute_not_exists(sk)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise c.ErrorHttp(409, "Ya habias confirmado este reporte")
        raise
    actualizado = c.reportes.update_item(
        Key={"reportId": report_id},
        UpdateExpression="SET confirmaciones = if_not_exists(confirmaciones, :cero) + :uno, actualizadoEn = :f",
        ExpressionAttributeValues={":cero": 0, ":uno": 1, ":f": c.ahora()},
        ReturnValues="ALL_NEW",
    )["Attributes"]
    return c.respuesta(200, {"confirmaciones": int(actualizado["confirmaciones"])})


def comentar(evento):
    sesion = c.usuario_actual(evento)
    report_id = _id(evento)
    _reporte(report_id)
    datos = c.cuerpo_json(evento)
    c.requerido(datos, "texto")
    momento = c.ahora()
    c.interacciones.put_item(Item={
        "reportId": report_id,
        "sk": "COM#%s#%s" % (momento, c.nuevo_id("cmt")),
        "tipo": "comentario",
        "texto": datos["texto"].strip()[:500],
        "userId": sesion["sub"],
        "autorNombre": sesion.get("nombre", ""),
        "oficial": sesion.get("rol") == "municipio",
        "creadoEn": momento,
    })
    c.reportes.update_item(
        Key={"reportId": report_id},
        UpdateExpression="SET comentarios = if_not_exists(comentarios, :cero) + :uno, actualizadoEn = :f",
        ExpressionAttributeValues={":cero": 0, ":uno": 1, ":f": momento},
    )
    return c.respuesta(201, {"mensaje": "Comentario publicado"})


def validar_solucion(evento):
    """El ciudadano confirma si el problema realmente quedo resuelto."""
    sesion = c.usuario_actual(evento)
    report_id = _id(evento)
    reporte = _reporte(report_id)
    if reporte["estado"] != "Resuelto":
        raise c.ErrorHttp(400, "El reporte todavia no esta marcado como Resuelto")
    datos = c.cuerpo_json(evento)
    resuelto = bool(datos.get("resuelto"))

    try:
        c.interacciones.put_item(
            Item={
                "reportId": report_id,
                "sk": "VAL#%s" % sesion["sub"],
                "tipo": "validacion",
                "userId": sesion["sub"],
                "resuelto": resuelto,
                "creadoEn": c.ahora(),
            },
            ConditionExpression="attribute_not_exists(sk)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise c.ErrorHttp(409, "Ya habias respondido si el problema quedo resuelto")
        raise

    campo = "validacionesSi" if resuelto else "validacionesNo"
    actualizado = c.reportes.update_item(
        Key={"reportId": report_id},
        UpdateExpression="SET #campo = if_not_exists(#campo, :cero) + :uno, actualizadoEn = :f",
        ExpressionAttributeNames={"#campo": campo},
        ExpressionAttributeValues={":cero": 0, ":uno": 1, ":f": c.ahora()},
        ReturnValues="ALL_NEW",
    )["Attributes"]

    negativas = int(actualizado.get("validacionesNo", 0))
    positivas = int(actualizado.get("validacionesSi", 0))
    reabierto = False
    if negativas >= 2 and negativas > positivas:
        momento = c.ahora()
        c.reportes.update_item(
            Key={"reportId": report_id},
            UpdateExpression="SET estado = :e, actualizadoEn = :f",
            ExpressionAttributeValues={":e": "En revisión", ":f": momento},
        )
        c.interacciones.put_item(Item={
            "reportId": report_id, "sk": "HIST#%s" % momento, "tipo": "historial",
            "estado": "En revisión", "autor": "Sistema",
            "mensaje": "Reabierto: los ciudadanos indican que el problema continua",
            "creadoEn": momento,
        })
        c.publicar_evento("reporte.reabierto", {
            "reportId": report_id, "titulo": reporte["titulo"], "estado": "En revisión",
            "destinatarios": [reporte["autorEmail"]],
        })
        reabierto = True

    return c.respuesta(200, {"validacionesSi": positivas, "validacionesNo": negativas, "reabierto": reabierto})


def _id(evento):
    report_id = (evento.get("pathParameters") or {}).get("id", "")
    if not report_id:
        raise c.ErrorHttp(400, "Falta el identificador del reporte")
    return report_id


def _reporte(report_id):
    item = c.reportes.get_item(Key={"reportId": report_id}).get("Item")
    if not item:
        raise c.ErrorHttp(404, "El reporte no existe")
    return item


RUTAS = {
    "POST /reportes/{id}/confirmaciones": confirmar,
    "POST /reportes/{id}/comentarios": comentar,
    "POST /reportes/{id}/validacion": validar_solucion,
}


def handler(evento, contexto):  # noqa: ARG001
    return c.enrutar(evento, RUTAS)
