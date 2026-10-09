"""Lambda del panel de la cuenta municipal simulada."""
from boto3.dynamodb.conditions import Key

import common as c


def bandeja(evento):
    """Lista de reportes para el panel, ordenada por prioridad (confirmaciones)."""
    c.solo_municipio(evento)
    parametros = evento.get("queryStringParameters") or {}
    if parametros.get("estado"):
        items = c.reportes.query(
            IndexName="estado-index",
            KeyConditionExpression=Key("estado").eq(parametros["estado"]),
            ScanIndexForward=False,
        ).get("Items", [])
    else:
        items = c.reportes.scan().get("Items", [])

    if parametros.get("categoria"):
        items = [r for r in items if r.get("categoria") == parametros["categoria"]]

    items.sort(key=lambda r: (int(r.get("confirmaciones", 0)), r["creadoEn"]), reverse=True)
    resumen = {estado: 0 for estado in c.ESTADOS}
    for r in items:
        resumen[r["estado"]] = resumen.get(r["estado"], 0) + 1

    return c.respuesta(200, {
        "resumen": resumen,
        "total": len(items),
        "reportes": [{
            "reportId": r["reportId"], "titulo": r["titulo"], "categoria": r["categoria"],
            "estado": r["estado"], "direccion": r.get("direccion", ""),
            "lat": float(r["lat"]), "lng": float(r["lng"]),
            "confirmaciones": int(r.get("confirmaciones", 0)),
            "autorNombre": r.get("autorNombre", ""), "creadoEn": r["creadoEn"],
            "foto": c.url_publica(r.get("fotoKey", "")),
        } for r in items],
    })


def cambiar_estado(evento):
    """Cambia el estado del reporte, responde al ciudadano y adjunta la evidencia."""
    sesion = c.solo_municipio(evento)
    report_id = (evento.get("pathParameters") or {}).get("id", "")
    datos = c.cuerpo_json(evento)
    c.requerido(datos, "estado")
    nuevo_estado = datos["estado"]
    if nuevo_estado not in c.ESTADOS:
        raise c.ErrorHttp(400, "Estado no valido. Estados permitidos: " + ", ".join(c.ESTADOS))

    reporte = c.reportes.get_item(Key={"reportId": report_id}).get("Item")
    if not reporte:
        raise c.ErrorHttp(404, "El reporte no existe")
    if nuevo_estado == "Resuelto" and not datos.get("evidenciaKey"):
        raise c.ErrorHttp(400, "Para cerrar un reporte debes adjuntar la evidencia de la solucion")

    momento = c.ahora()
    expresion = "SET estado = :e, actualizadoEn = :f, respuestaMunicipal = :r"
    valores = {
        ":e": nuevo_estado,
        ":f": momento,
        ":r": datos.get("respuesta", "").strip()[:500],
    }
    if datos.get("evidenciaKey"):
        expresion += ", evidenciaKey = :ev"
        valores[":ev"] = datos["evidenciaKey"]

    c.reportes.update_item(
        Key={"reportId": report_id},
        UpdateExpression=expresion,
        ExpressionAttributeValues=valores,
    )
    c.interacciones.put_item(Item={
        "reportId": report_id, "sk": "HIST#%s" % momento, "tipo": "historial",
        "estado": nuevo_estado, "autor": sesion.get("nombre", "Cuenta municipal"),
        "mensaje": datos.get("respuesta", "").strip()[:500] or "Actualizacion de estado",
        "creadoEn": momento,
    })

    interesados = c.interacciones.query(
        KeyConditionExpression=Key("reportId").eq(report_id)
    ).get("Items", [])
    destinatarios = [reporte["autorEmail"]] + [
        i["email"] for i in interesados if i["tipo"] == "confirmacion" and i.get("email")
    ]
    c.publicar_evento("reporte.estado", {
        "reportId": report_id,
        "titulo": reporte["titulo"],
        "estado": nuevo_estado,
        "respuesta": datos.get("respuesta", ""),
        "evidencia": c.url_publica(datos.get("evidenciaKey", "")),
        "destinatarios": sorted(set(destinatarios)),
    })
    return c.respuesta(200, {"reportId": report_id, "estado": nuevo_estado, "actualizadoEn": momento})


def url_evidencia(evento):
    c.solo_municipio(evento)
    datos = c.cuerpo_json(evento)
    tipo = datos.get("contentType", "image/jpeg")
    if tipo not in ("image/jpeg", "image/png", "image/webp"):
        raise c.ErrorHttp(400, "Solo se permiten imagenes JPEG, PNG o WEBP")
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[tipo]
    key = "evidencias/%s.%s" % (c.nuevo_id("ev"), extension)
    return c.respuesta(200, {"key": key, "url": c.url_prefirmada(key, tipo), "urlPublica": c.url_publica(key)})


RUTAS = {
    "GET /admin/reportes": bandeja,
    "PATCH /admin/reportes/{id}/estado": cambiar_estado,
    "POST /admin/evidencias": url_evidencia,
}


def handler(evento, contexto):  # noqa: ARG001
    return c.enrutar(evento, RUTAS)
