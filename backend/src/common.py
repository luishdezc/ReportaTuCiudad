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
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLA_USUARIOS = os.environ.get("TABLA_USUARIOS", "")
TABLA_REPORTES = os.environ.get("TABLA_REPORTES", "")
TABLA_INTERACCIONES = os.environ.get("TABLA_INTERACCIONES", "")
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


def nuevo_id(prefijo):
    return f"{prefijo}_{uuid.uuid4().hex[:12]}"


def cuerpo_json(evento):
    crudo = evento.get("body") or "{}"
    if evento.get("isBase64Encoded"):
        crudo = base64.b64decode(crudo).decode("utf-8")
    try:
        return json.loads(crudo)
    except json.JSONDecodeError:
        raise ErrorHttp(400, "El cuerpo de la peticion no es JSON valido")


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
            raise ErrorHttp(500, "No se pudo leer el secreto de la aplicacion: %s" % exc)
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
        raise ErrorHttp(401, "Token invalido")
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
