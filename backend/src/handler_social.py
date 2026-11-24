"""Lambda de la capa comunitaria: perfiles, feed de la ciudad, estadisticas
y notificaciones dentro de la aplicacion.

Lo que convierte la plataforma en algo mas que un buzon: cada ciudadano tiene
un perfil con lo que ha aportado, la ciudad tiene un muro con lo que esta
pasando, y cada quien recibe avisos de los reportes que sigue.
"""
import common as c
from boto3.dynamodb.conditions import Key

# Insignias: (clave, titulo, descripcion, campo, umbral)
INSIGNIAS = [
    ("primer_reporte", "Primer reporte", "Levantaste tu primer reporte", "reportes", 1),
    ("vigilante", "Vecino vigilante", "Cinco reportes levantados", "reportes", 5),
    ("cronista", "Cronista de la colonia", "Quince reportes levantados", "reportes", 15),
    ("respaldo", "Buen respaldo", "Confirmaste cinco reportes de otros", "confirmaciones", 5),
    ("conversador", "Conversador", "Diez comentarios publicados", "comentarios", 10),
    ("resolutivo", "Con resultados", "Tres de tus reportes llegaron a Resuelto", "resueltos", 3),
]


# ===========================================================================
# Perfil publico
# ===========================================================================
def perfil(evento):
    """Perfil de un ciudadano: lo que ha aportado y sus insignias."""
    user_id = (evento.get("pathParameters") or {}).get("id", "")
    usuario = c.usuarios.get_item(Key={"userId": user_id}).get("Item")
    if not usuario:
        raise c.ErrorHttp(404, "Ese perfil no existe")

    mios = c.reportes.query(
        IndexName="autor-index",
        KeyConditionExpression=Key("autorId").eq(user_id),
        ScanIndexForward=False,
        Limit=50,
    ).get("Items", [])

    resueltos = len([r for r in mios if r.get("estado") == "Resuelto"])
    apoyos = sum(int(r.get("confirmaciones", 0)) for r in mios)

    estadisticas = {
        "reportes": len(mios),
        "resueltos": resueltos,
        "apoyosRecibidos": apoyos,
        "confirmaciones": int(usuario.get("confirmacionesDadas", 0)),
        "comentarios": int(usuario.get("comentariosEscritos", 0)),
    }

    return c.respuesta(200, {
        "usuario": {
            "userId": usuario["userId"],
            "nombre": usuario["nombre"],
            "colonia": usuario.get("colonia", ""),
            "rol": usuario.get("rol", "ciudadano"),
            "desde": usuario.get("creadoEn", ""),
        },
        "estadisticas": estadisticas,
        "insignias": _insignias(estadisticas),
        "reportes": [{
            "reportId": r["reportId"],
            "titulo": r["titulo"],
            "categoria": r["categoria"],
            "estado": r["estado"],
            "confirmaciones": int(r.get("confirmaciones", 0)),
            "creadoEn": r["creadoEn"],
        } for r in mios[:20]],
    })


def _insignias(estadisticas):
    """Las insignias se calculan al vuelo: no hay nada que mantener al dia."""
    ganadas = []
    for clave, titulo, descripcion, campo, umbral in INSIGNIAS:
        valor = estadisticas.get(campo, 0)
        ganadas.append({
            "clave": clave,
            "titulo": titulo,
            "descripcion": descripcion,
            "obtenida": valor >= umbral,
            "avance": min(valor, umbral),
            "meta": umbral,
        })
    return ganadas


# ===========================================================================
# Feed de actividad de la ciudad
# ===========================================================================
def feed(evento):
    """Lo que ha pasado en la ciudad en los ultimos dias."""
    parametros = evento.get("queryStringParameters") or {}
    limite = min(int(parametros.get("limite", 40)), 100)

    eventos = []
    for dia in _ultimos_dias(c.DIAS_DE_FEED):
        resultado = c.actividad.query(
            KeyConditionExpression=Key("dia").eq(dia),
            ScanIndexForward=False,
            Limit=limite,
        )
        eventos.extend(resultado.get("Items", []))

    eventos.sort(key=lambda e: e.get("creadoEn", ""), reverse=True)
    return c.respuesta(200, {"eventos": [{
        "tipo": e.get("tipo", ""),
        "reportId": e.get("reportId", ""),
        "titulo": e.get("titulo", ""),
        "categoria": e.get("categoria", ""),
        "estado": e.get("estado", ""),
        "actor": e.get("actor", ""),
        "detalle": e.get("detalle", ""),
        "creadoEn": e.get("creadoEn", ""),
    } for e in eventos[:limite]]})


def _ultimos_dias(cuantos):
    import time
    hoy = time.time()
    return [time.strftime("%Y-%m-%d", time.gmtime(hoy - i * 86400)) for i in range(cuantos)]


# ===========================================================================
# Estadisticas publicas de la ciudad
# ===========================================================================
def estadisticas(evento):  # noqa: ARG001
    """Numeros de la ciudad, tomados de contadores atomicos."""
    totales = c.actividad.get_item(
        Key={"dia": "TOTALES", "sk": "GLOBAL"}).get("Item", {})

    creados = int(totales.get("reportesCreados", 0))
    resueltos = int(totales.get("reportesResueltos", 0))
    minutos = int(totales.get("minutosResolucionAcumulados", 0))

    por_categoria = {}
    for clave, valor in totales.items():
        if clave.startswith("cat_"):
            por_categoria[clave[4:].replace("_", " ")] = int(valor)

    return c.respuesta(200, {
        "reportesCreados": creados,
        "reportesResueltos": resueltos,
        "confirmaciones": int(totales.get("confirmaciones", 0)),
        "comentarios": int(totales.get("comentarios", 0)),
        "reabiertos": int(totales.get("reabiertos", 0)),
        "porcentajeResuelto": round(resueltos * 100.0 / creados, 1) if creados else 0,
        "horasPromedioResolucion": round(minutos / 60.0 / resueltos, 1) if resueltos else 0,
        "porCategoria": por_categoria,
    })


# ===========================================================================
# Notificaciones dentro de la aplicacion
# ===========================================================================
def listar_notificaciones(evento):
    sesion = c.usuario_actual(evento)
    resultado = c.notificaciones.query(
        KeyConditionExpression=Key("userId").eq(sesion["sub"]),
        ScanIndexForward=False,
        Limit=30,
    ).get("Items", [])

    return c.respuesta(200, {
        "sinLeer": len([n for n in resultado if not n.get("leida")]),
        "notificaciones": [{
            "sk": n["sk"],
            "tipo": n.get("tipo", "aviso"),
            "titulo": n.get("titulo", ""),
            "cuerpo": n.get("cuerpo", ""),
            "reportId": n.get("reportId", ""),
            "leida": bool(n.get("leida")),
            "creadoEn": n.get("creadoEn", ""),
        } for n in resultado],
    })


def marcar_leidas(evento):
    """Marca como leidas todas las notificaciones del usuario."""
    sesion = c.usuario_actual(evento)
    pendientes = [n for n in c.notificaciones.query(
        KeyConditionExpression=Key("userId").eq(sesion["sub"]),
        Limit=100,
    ).get("Items", []) if not n.get("leida")]

    for notificacion in pendientes:
        c.notificaciones.update_item(
            Key={"userId": sesion["sub"], "sk": notificacion["sk"]},
            UpdateExpression="SET leida = :v",
            ExpressionAttributeValues={":v": True},
        )
    return c.respuesta(200, {"marcadas": len(pendientes)})


RUTAS = {
    "GET /usuarios/{id}/perfil": perfil,
    "GET /actividad": feed,
    "GET /estadisticas": estadisticas,
    "GET /notificaciones": listar_notificaciones,
    "POST /notificaciones/leidas": marcar_leidas,
}


def handler(evento, contexto):  # noqa: ARG001
    return c.enrutar(evento, RUTAS)
