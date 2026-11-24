"""Utilidades compartidas por las funciones Lambda de ReportaTuCiudad."""
import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLA_USUARIOS = os.environ.get("TABLA_USUARIOS", "")
TABLA_REPORTES = os.environ.get("TABLA_REPORTES", "")
TABLA_INTERACCIONES = os.environ.get("TABLA_INTERACCIONES", "")
TABLA_NOTIFICACIONES = os.environ.get("TABLA_NOTIFICACIONES", "")
TABLA_ACTIVIDAD = os.environ.get("TABLA_ACTIVIDAD", "")
BUCKET_MEDIA = os.environ.get("BUCKET_MEDIA", "")
COLA_EVENTOS = os.environ.get("COLA_EVENTOS", "")
SECRETO_JWT = os.environ.get("SECRETO_JWT", "")
TOPICO_SNS = os.environ.get("TOPICO_SNS", "")

ESTADOS = ["Reportado", "En revisión", "Asignado", "En proceso", "Resuelto"]
CATEGORIAS = [
    "Bache",
    "Luminaria dañada",
    "Acumulación de basura",
    "Fuga de agua",
    "Árbol caído",
    "Semáforo dañado",
    "Otro",
]

_dynamodb = boto3.resource("dynamodb", region_name=REGION)
_s3 = boto3.client("s3", region_name=REGION)
_sqs = boto3.client("sqs", region_name=REGION)
_secrets = boto3.client("secretsmanager", region_name=REGION)

usuarios = _dynamodb.Table(TABLA_USUARIOS) if TABLA_USUARIOS else None
reportes = _dynamodb.Table(TABLA_REPORTES) if TABLA_REPORTES else None
interacciones = _dynamodb.Table(TABLA_INTERACCIONES) if TABLA_INTERACCIONES else None
notificaciones = _dynamodb.Table(TABLA_NOTIFICACIONES) if TABLA_NOTIFICACIONES else None
actividad = _dynamodb.Table(TABLA_ACTIVIDAD) if TABLA_ACTIVIDAD else None

_cache_secreto = {}


class ErrorHttp(Exception):
    def __init__(self, codigo, mensaje):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


class CodificadorJson(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


CABECERAS = {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,PATCH,OPTIONS",
}


def respuesta(codigo, cuerpo):
    return {
        "statusCode": codigo,
        "headers": CABECERAS,
        "body": json.dumps(cuerpo, cls=CodificadorJson, ensure_ascii=False),
    }


def ahora():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ahora_preciso():
    """Marca de tiempo con microsegundos.

    La usan los items de historial: su llave de orden es la fecha, y con
    precision de segundos dos cambios seguidos comparten llave y el segundo
    sobrescribe al primero.
    """
    instante = time.time()
    return "%s.%06dZ" % (
        time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(instante)),
        int((instante % 1) * 1000000),
    )


def nuevo_id(prefijo):
    return f"{prefijo}_{uuid.uuid4().hex[:12]}"


def cuerpo_json(evento):
    crudo = evento.get("body") or "{}"
    if evento.get("isBase64Encoded"):
        crudo = base64.b64decode(crudo).decode("utf-8")
    try:
        return json.loads(crudo)
    except json.JSONDecodeError:
        raise ErrorHttp(400, "El cuerpo de la peticion no es JSON valido") from None


def requerido(datos, *campos):
    faltantes = [c for c in campos if not str(datos.get(c, "")).strip()]
    if faltantes:
        raise ErrorHttp(400, "Faltan campos obligatorios: " + ", ".join(faltantes))


def llave_jwt():
    if "valor" not in _cache_secreto:
        try:
            secreto = _secrets.get_secret_value(SecretId=SECRETO_JWT)
            _cache_secreto["valor"] = json.loads(secreto["SecretString"])["jwt_secret"]
        except (ClientError, KeyError, json.JSONDecodeError) as exc:
            raise ErrorHttp(500, "No se pudo leer el secreto de la aplicacion: %s" % exc) from exc
    return _cache_secreto["valor"]


def hash_password(password, salt=None):
    salt = salt or uuid.uuid4().hex
    derivada = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000)
    return "%s$%s" % (salt, derivada.hex())


def verificar_password(password, almacenado):
    try:
        salt, _ = almacenado.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), almacenado)


def _b64(datos):
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def _b64d(texto):
    relleno = "=" * (-len(texto) % 4)
    return base64.urlsafe_b64decode(texto + relleno)


def crear_token(usuario, horas=12):
    cabecera = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    carga = _b64(json.dumps({
        "sub": usuario["userId"],
        "email": usuario["email"],
        "nombre": usuario.get("nombre", ""),
        "rol": usuario.get("rol", "ciudadano"),
        "exp": int(time.time()) + horas * 3600,
    }).encode())
    firma = hmac.new(llave_jwt().encode(), ("%s.%s" % (cabecera, carga)).encode(), hashlib.sha256).digest()
    return "%s.%s.%s" % (cabecera, carga, _b64(firma))


def leer_token(token):
    try:
        cabecera, carga, firma = token.split(".")
    except ValueError:
        raise ErrorHttp(401, "Token invalido") from None
    esperada = _b64(hmac.new(llave_jwt().encode(), ("%s.%s" % (cabecera, carga)).encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(esperada, firma):
        raise ErrorHttp(401, "Token invalido")
    datos = json.loads(_b64d(carga))
    if datos.get("exp", 0) < time.time():
        raise ErrorHttp(401, "La sesion expiro, inicia sesion de nuevo")
    return datos


def usuario_actual(evento, obligatorio=True):
    cabeceras = {k.lower(): v for k, v in (evento.get("headers") or {}).items()}
    autorizacion = cabeceras.get("authorization", "")
    if not autorizacion.lower().startswith("bearer "):
        if obligatorio:
            raise ErrorHttp(401, "Se requiere iniciar sesion")
        return None
    return leer_token(autorizacion.split(" ", 1)[1].strip())


def solo_municipio(evento):
    usuario = usuario_actual(evento)
    if usuario.get("rol") != "municipio":
        raise ErrorHttp(403, "Solo la cuenta municipal puede realizar esta accion")
    return usuario


def publicar_evento(tipo, datos):
    """Encola un evento en SQS para que el notificador lo procese."""
    if not COLA_EVENTOS:
        return
    _sqs.send_message(
        QueueUrl=COLA_EVENTOS,
        MessageBody=json.dumps(
            {"tipo": tipo, "datos": datos, "fecha": ahora()},
            cls=CodificadorJson, ensure_ascii=False,
        ),
    )


def url_publica(key):
    if not key:
        return None
    return "https://%s.s3.amazonaws.com/%s" % (BUCKET_MEDIA, key)


def url_prefirmada(key, tipo_contenido):
    return _s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": BUCKET_MEDIA, "Key": key, "ContentType": tipo_contenido},
        ExpiresIn=300,
    )


def enrutar(evento, rutas):
    """Despacha segun la routeKey del API HTTP (ej. 'POST /reportes')."""
    clave = evento.get("routeKey", "")
    manejador = rutas.get(clave)
    if not manejador:
        return respuesta(404, {"error": "Ruta no encontrada: %s" % clave})
    try:
        return manejador(evento)
    except ErrorHttp as exc:
        return respuesta(exc.codigo, {"error": exc.mensaje})
    except ClientError as exc:
        print("ERROR AWS:", exc)
        return respuesta(500, {"error": "Error al comunicarse con los servicios de AWS"})
    except Exception as exc:  # noqa: BLE001
        print("ERROR NO CONTROLADO:", repr(exc))
        return respuesta(500, {"error": "Error interno del servidor"})


# ===========================================================================
# Metricas de aplicacion
# ===========================================================================
# Se publican con el formato EMF (Embedded Metric Format): la Lambda imprime
# una linea de JSON y CloudWatch la convierte en metrica. Asi no hace falta
# llamar a PutMetricData, que costaria una peticion de red por evento.

ESPACIO_METRICAS = "ReportaTuCiudad"


def metrica(nombre, valor=1, unidad="Count", dimensiones=None):
    """Publica una metrica de aplicacion en CloudWatch."""
    dimensiones = dict(dimensiones or {})
    dimensiones["Ambiente"] = os.environ.get("AMBIENTE", "dev")

    # Dos juegos de dimensiones: el total por ambiente y, si las hay, el
    # desglose. Asi el dashboard puede graficar ambos sin instrumentar dos veces.
    juegos = [["Ambiente"]]
    if len(dimensiones) > 1:
        juegos.append(sorted(dimensiones.keys()))

    documento = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [{
                "Namespace": ESPACIO_METRICAS,
                "Dimensions": juegos,
                "Metrics": [{"Name": nombre, "Unit": unidad}],
            }],
        },
        nombre: valor,
    }
    documento.update(dimensiones)
    print(json.dumps(documento, ensure_ascii=False))


def minutos_desde(iso):
    """Minutos transcurridos desde una marca ISO-8601, para medir resoluciones."""
    try:
        limpio = iso.replace("Z", "").split(".")[0]
        instante = time.mktime(time.strptime(limpio, "%Y-%m-%dT%H:%M:%S"))
        return max(0, int((time.time() - (instante - time.timezone)) / 60))
    except (ValueError, TypeError):
        return 0


# ===========================================================================
# Actividad de la ciudad y estadisticas agregadas
# ===========================================================================
# La tabla de actividad se particiona por dia (YYYY-MM-DD) para no concentrar
# todas las escrituras en una sola particion. Los totales viven en la
# particion reservada "TOTALES" y se actualizan con sumas atomicas.

DIAS_DE_FEED = 3
VIDA_ACTIVIDAD_DIAS = 30


def registrar_actividad(tipo, reporte, detalle=""):
    """Agrega un evento al feed publico de la ciudad."""
    if not actividad:
        return
    momento = ahora_preciso()
    actividad.put_item(Item={
        "dia": momento[:10],
        "sk": "%s#%s" % (momento, nuevo_id("act")),
        "tipo": tipo,
        "reportId": reporte.get("reportId", ""),
        "titulo": reporte.get("titulo", ""),
        "categoria": reporte.get("categoria", ""),
        "estado": reporte.get("estado", ""),
        "colonia": reporte.get("colonia", ""),
        "actor": reporte.get("actor", ""),
        "detalle": detalle[:200],
        "creadoEn": momento,
        "expiraEn": int(time.time()) + VIDA_ACTIVIDAD_DIAS * 86400,
    })


def sumar_totales(**campos):
    """Suma atomica sobre los contadores de la ciudad."""
    if not actividad or not campos:
        return
    expresion = "ADD " + ", ".join("#c%d :v%d" % (i, i) for i in range(len(campos)))
    nombres = {"#c%d" % i: k for i, k in enumerate(campos)}
    valores = {":v%d" % i: v for i, v in enumerate(campos.values())}
    actividad.update_item(
        Key={"dia": "TOTALES", "sk": "GLOBAL"},
        UpdateExpression=expresion,
        ExpressionAttributeNames=nombres,
        ExpressionAttributeValues=valores,
    )


# ===========================================================================
# Notificaciones dentro de la aplicacion
# ===========================================================================
VIDA_NOTIFICACION_DIAS = 60


def notificar_en_app(usuarios, titulo, cuerpo, report_id="", tipo="aviso"):
    """Deja un aviso en la campana de cada usuario indicado."""
    if not notificaciones:
        return
    destinos = [u for u in dict.fromkeys(usuarios) if u]
    if not destinos:
        return
    momento = ahora_preciso()
    with notificaciones.batch_writer() as lote:
        for user_id in destinos:
            lote.put_item(Item={
                "userId": user_id,
                "sk": "NOT#%s#%s" % (momento, nuevo_id("n")),
                "tipo": tipo,
                "titulo": titulo[:120],
                "cuerpo": cuerpo[:400],
                "reportId": report_id,
                "leida": False,
                "creadoEn": momento,
                "expiraEn": int(time.time()) + VIDA_NOTIFICACION_DIAS * 86400,
            })


def interesados(report_id, reporte):
    """Quienes siguen un reporte: su autor, quienes lo confirmaron y sus seguidores.

    Devuelve (ids de usuario, correos). Los ids alimentan la campana de avisos
    dentro de la aplicacion; los correos, las notificaciones por SNS.
    """
    items = interacciones.query(
        KeyConditionExpression=Key("reportId").eq(report_id)).get("Items", [])
    ids = {reporte.get("autorId", "")}
    correos = {reporte.get("autorEmail", "")}
    for item in items:
        if item.get("tipo") in ("confirmacion", "seguidor"):
            ids.add(item.get("userId", ""))
            if item.get("email"):
                correos.add(item["email"])
    return sorted(x for x in ids if x), sorted(x for x in correos if x)


def sumar_al_usuario(user_id, campo, valor=1):
    """Contadores del perfil (confirmaciones dadas, comentarios escritos)."""
    if not usuarios or not user_id:
        return
    usuarios.update_item(
        Key={"userId": user_id},
        UpdateExpression="ADD #c :v",
        ExpressionAttributeNames={"#c": campo},
        ExpressionAttributeValues={":v": valor},
    )
