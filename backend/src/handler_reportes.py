"""Lambda de reportes: alta, consulta en el mapa y URLs de carga de fotos."""
from boto3.dynamodb.conditions import Key

import common as c


def url_de_carga(evento):
    """Devuelve una URL prefirmada para que el navegador suba la foto directo a S3."""
    sesion = c.usuario_actual(evento)
    datos = c.cuerpo_json(evento)
    tipo = datos.get("contentType", "image/jpeg")
    if tipo not in ("image/jpeg", "image/png", "image/webp"):
        raise c.ErrorHttp(400, "Solo se permiten imagenes JPEG, PNG o WEBP")
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[tipo]
    key = "reportes/%s/%s.%s" % (sesion["sub"], c.nuevo_id("img"), extension)
    return c.respuesta(200, {"key": key, "url": c.url_prefirmada(key, tipo), "urlPublica": c.url_publica(key)})


def crear(evento):
    sesion = c.usuario_actual(evento)
    datos = c.cuerpo_json(evento)
    c.requerido(datos, "titulo", "categoria", "descripcion")
    if datos["categoria"] not in c.CATEGORIAS:
        raise c.ErrorHttp(400, "Categoria no valida")
    try:
        lat = round(float(datos["lat"]), 6)
        lng = round(float(datos["lng"]), 6)
    except (KeyError, TypeError, ValueError):
        raise c.ErrorHttp(400, "Debes marcar la ubicacion del problema en el mapa")

    reporte = {
        "reportId": c.nuevo_id("rep"),
        "titulo": datos["titulo"].strip()[:120],
        "categoria": datos["categoria"],
        "descripcion": datos["descripcion"].strip()[:1000],
        "direccion": datos.get("direccion", "").strip()[:160],
        "lat": str(lat),
        "lng": str(lng),
        "fotoKey": datos.get("fotoKey", ""),
        "estado": "Reportado",
        "autorId": sesion["sub"],
        "autorNombre": sesion.get("nombre", ""),
        "autorEmail": sesion["email"],
        "confirmaciones": 0,
        "comentarios": 0,
        "validacionesSi": 0,
        "validacionesNo": 0,
        "creadoEn": c.ahora(),
        "actualizadoEn": c.ahora(),
    }
    c.reportes.put_item(Item=reporte)
    c.interacciones.put_item(Item={
        "reportId": reporte["reportId"],
        "sk": "HIST#%s" % reporte["creadoEn"],
        "tipo": "historial",
        "estado": "Reportado",
        "mensaje": "Reporte recibido por la plataforma",
        "autor": "Sistema",
        "creadoEn": reporte["creadoEn"],
    })
    c.publicar_evento("reporte.creado", {
        "reportId": reporte["reportId"],
        "titulo": reporte["titulo"],
        "categoria": reporte["categoria"],
        "estado": reporte["estado"],
        "destinatarios": [reporte["autorEmail"]],
    })
    return c.respuesta(201, {"reporte": _salida(reporte)})


def listar(evento):
    parametros = evento.get("queryStringParameters") or {}
    estado = parametros.get("estado")
    limite = min(int(parametros.get("limite", 100)), 200)

    if estado:
        resultado = c.reportes.query(
            IndexName="estado-index",
            KeyConditionExpression=Key("estado").eq(estado),
            ScanIndexForward=False,
            Limit=limite,
        )
    else:
        resultado = c.reportes.scan(Limit=limite)

    items = [_salida(r) for r in resultado.get("Items", [])]
    if parametros.get("categoria"):
        items = [r for r in items if r["categoria"] == parametros["categoria"]]
    if parametros.get("mios") == "1":
        sesion = c.usuario_actual(evento)
        items = [r for r in items if r["autorId"] == sesion["sub"]]
    items.sort(key=lambda r: r["creadoEn"], reverse=True)
    return c.respuesta(200, {"total": len(items), "reportes": items})


def detalle(evento):
    report_id = (evento.get("pathParameters") or {}).get("id", "")
    item = c.reportes.get_item(Key={"reportId": report_id}).get("Item")
    if not item:
        raise c.ErrorHttp(404, "El reporte no existe")

    relacionadas = c.interacciones.query(
        KeyConditionExpression=Key("reportId").eq(report_id)
    ).get("Items", [])
    comentarios = sorted(
        [i for i in relacionadas if i["tipo"] == "comentario"], key=lambda i: i["creadoEn"]
    )
    historial = sorted(
        [i for i in relacionadas if i["tipo"] == "historial"], key=lambda i: i["creadoEn"]
    )
    confirmadores = [i["userId"] for i in relacionadas if i["tipo"] == "confirmacion"]
    return c.respuesta(200, {
        "reporte": _salida(item),
        "comentarios": [
            {"autor": i.get("autorNombre", ""), "texto": i.get("texto", ""),
             "oficial": i.get("oficial", False), "creadoEn": i["creadoEn"]}
            for i in comentarios
        ],
        "historial": [
            {"estado": i.get("estado", ""), "mensaje": i.get("mensaje", ""),
             "autor": i.get("autor", ""), "creadoEn": i["creadoEn"]}
            for i in historial
        ],
        "confirmadores": confirmadores,
    })


def _salida(reporte):
    return {
        "reportId": reporte["reportId"],
        "titulo": reporte["titulo"],
        "categoria": reporte["categoria"],
        "descripcion": reporte["descripcion"],
        "direccion": reporte.get("direccion", ""),
        "lat": float(reporte["lat"]),
        "lng": float(reporte["lng"]),
        "estado": reporte["estado"],
        "foto": c.url_publica(reporte.get("fotoKey", "")),
        "evidencia": c.url_publica(reporte.get("evidenciaKey", "")),
        "respuestaMunicipal": reporte.get("respuestaMunicipal", ""),
        "autorId": reporte["autorId"],
        "autorNombre": reporte.get("autorNombre", ""),
        "confirmaciones": int(reporte.get("confirmaciones", 0)),
        "comentarios": int(reporte.get("comentarios", 0)),
        "validacionesSi": int(reporte.get("validacionesSi", 0)),
        "validacionesNo": int(reporte.get("validacionesNo", 0)),
        "creadoEn": reporte["creadoEn"],
        "actualizadoEn": reporte.get("actualizadoEn", reporte["creadoEn"]),
    }


RUTAS = {
    "POST /reportes": crear,
    "GET /reportes": listar,
    "GET /reportes/{id}": detalle,
    "POST /reportes/carga": url_de_carga,
}


def handler(evento, contexto):  # noqa: ARG001
    return c.enrutar(evento, RUTAS)
