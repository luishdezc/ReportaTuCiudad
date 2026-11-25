"""Lambda del panel de la cuenta municipal simulada."""
import common as c
from boto3.dynamodb.conditions import Key


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
    marca = c.ahora_preciso()
    c.interacciones.put_item(Item={
        "reportId": report_id, "sk": "HIST#%s" % marca, "tipo": "historial",
        "estado": nuevo_estado, "autor": sesion.get("nombre", "Cuenta municipal"),
        "mensaje": datos.get("respuesta", "").strip()[:500] or "Actualizacion de estado",
        "creadoEn": marca,
    })

    ids, correos = c.interesados(report_id, reporte)
    c.publicar_evento("reporte.estado", {
        "reportId": report_id,
        "titulo": reporte["titulo"],
        "estado": nuevo_estado,
        "respuesta": datos.get("respuesta", ""),
        "evidencia": c.url_publica(datos.get("evidenciaKey", "")),
        "destinatarios": correos,
    })
    c.notificar_en_app(
        ids,
        "Tu reporte cambio a %s" % nuevo_estado,
        "\"%s\" ahora esta en %s. %s" % (
            reporte["titulo"], nuevo_estado, datos.get("respuesta", "")),
        report_id, tipo="estado")
    c.registrar_actividad(
        "reporte.estado",
        dict(reporte, estado=nuevo_estado, actor=sesion.get("nombre", "Cuenta municipal")),
        detalle=datos.get("respuesta", ""))

    if nuevo_estado == "Resuelto" and reporte.get("estado") != "Resuelto":
        tardanza = c.minutos_desde(reporte["creadoEn"])
        c.sumar_totales(reportesResueltos=1, minutosResolucionAcumulados=tardanza)
        c.metrica("ReportesResueltos", dimensiones={"Categoria": reporte.get("categoria", "Otro")})
        c.metrica("MinutosHastaResolucion", valor=tardanza, unidad="None")

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
