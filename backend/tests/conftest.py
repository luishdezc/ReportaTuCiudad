"""Configuracion de las pruebas: simula DynamoDB, S3, SQS, SNS y Secrets Manager con moto.

Los modulos del backend crean sus clientes y tablas al importarse, asi que aqui se
levanta el entorno simulado ANTES de importarlos.
"""
import json
import os
import sys

import boto3
import pytest
from moto import mock_aws

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(RAIZ, "src")
sys.path.insert(0, SRC)

REGION = "us-east-1"
TABLA_USUARIOS = "pruebas-usuarios"
TABLA_REPORTES = "pruebas-reportes"
TABLA_INTERACCIONES = "pruebas-interacciones"
TABLA_NOTIFICACIONES = "pruebas-notificaciones"
TABLA_ACTIVIDAD = "pruebas-actividad"
BUCKET_MEDIA = "pruebas-media"
SECRETO = "pruebas-app-secrets"

# --- credenciales y variables de entorno falsas, antes de cualquier import ---
os.environ.update({
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "AWS_SECURITY_TOKEN": "testing",
    "AWS_SESSION_TOKEN": "testing",
    "AWS_REGION": REGION,
    "AWS_DEFAULT_REGION": REGION,
    "TABLA_USUARIOS": TABLA_USUARIOS,
    "TABLA_REPORTES": TABLA_REPORTES,
    "TABLA_INTERACCIONES": TABLA_INTERACCIONES,
    "TABLA_NOTIFICACIONES": TABLA_NOTIFICACIONES,
    "TABLA_ACTIVIDAD": TABLA_ACTIVIDAD,
    "BUCKET_MEDIA": BUCKET_MEDIA,
    "SECRETO_JWT": SECRETO,
    "AMBIENTE": "pruebas",
    "URL_FRONTEND": "http://ejemplo.local",
})

# --- entorno simulado ---
_mock = mock_aws()
_mock.start()

_ddb = boto3.client("dynamodb", region_name=REGION)
_ddb.create_table(
    TableName=TABLA_USUARIOS, BillingMode="PAY_PER_REQUEST",
    KeySchema=[{"AttributeName": "userId", "KeyType": "HASH"}],
    AttributeDefinitions=[{"AttributeName": "userId", "AttributeType": "S"},
                          {"AttributeName": "email", "AttributeType": "S"}],
    GlobalSecondaryIndexes=[{
        "IndexName": "email-index",
        "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
        "Projection": {"ProjectionType": "ALL"},
    }])
_ddb.create_table(
    TableName=TABLA_REPORTES, BillingMode="PAY_PER_REQUEST",
    KeySchema=[{"AttributeName": "reportId", "KeyType": "HASH"}],
    AttributeDefinitions=[{"AttributeName": "reportId", "AttributeType": "S"},
                          {"AttributeName": "estado", "AttributeType": "S"},
                          {"AttributeName": "creadoEn", "AttributeType": "S"},
                          {"AttributeName": "autorId", "AttributeType": "S"}],
    GlobalSecondaryIndexes=[
        {
            "IndexName": "estado-index",
            "KeySchema": [{"AttributeName": "estado", "KeyType": "HASH"},
                          {"AttributeName": "creadoEn", "KeyType": "RANGE"}],
            "Projection": {"ProjectionType": "ALL"},
        },
        {
            "IndexName": "autor-index",
            "KeySchema": [{"AttributeName": "autorId", "KeyType": "HASH"},
                          {"AttributeName": "creadoEn", "KeyType": "RANGE"}],
            "Projection": {"ProjectionType": "ALL"},
        },
    ])
_ddb.create_table(
    TableName=TABLA_INTERACCIONES, BillingMode="PAY_PER_REQUEST",
    KeySchema=[{"AttributeName": "reportId", "KeyType": "HASH"},
               {"AttributeName": "sk", "KeyType": "RANGE"}],
    AttributeDefinitions=[{"AttributeName": "reportId", "AttributeType": "S"},
                          {"AttributeName": "sk", "AttributeType": "S"}])

_ddb.create_table(
    TableName=TABLA_NOTIFICACIONES, BillingMode="PAY_PER_REQUEST",
    KeySchema=[{"AttributeName": "userId", "KeyType": "HASH"},
               {"AttributeName": "sk", "KeyType": "RANGE"}],
    AttributeDefinitions=[{"AttributeName": "userId", "AttributeType": "S"},
                          {"AttributeName": "sk", "AttributeType": "S"}])
_ddb.create_table(
    TableName=TABLA_ACTIVIDAD, BillingMode="PAY_PER_REQUEST",
    KeySchema=[{"AttributeName": "dia", "KeyType": "HASH"},
               {"AttributeName": "sk", "KeyType": "RANGE"}],
    AttributeDefinitions=[{"AttributeName": "dia", "AttributeType": "S"},
                          {"AttributeName": "sk", "AttributeType": "S"}])

boto3.client("s3", region_name=REGION).create_bucket(Bucket=BUCKET_MEDIA)

_cola = boto3.client("sqs", region_name=REGION).create_queue(QueueName="pruebas-eventos")
os.environ["COLA_EVENTOS"] = _cola["QueueUrl"]

_topico = boto3.client("sns", region_name=REGION).create_topic(Name="pruebas-notificaciones")
os.environ["TOPICO_SNS"] = _topico["TopicArn"]

boto3.client("secretsmanager", region_name=REGION).create_secret(
    Name=SECRETO, SecretString=json.dumps({"jwt_secret": "llave-de-pruebas-123456"}))

# --- ahora si, los modulos del backend ---
import common  # noqa: E402
import handler_admin  # noqa: E402
import handler_auth  # noqa: E402
import handler_interacciones  # noqa: E402
import handler_reportes  # noqa: E402
import handler_social  # noqa: E402


# =========================================================== utilidades
def evento(route_key, cuerpo=None, token=None, ruta=None, consulta=None):
    """Arma un evento de API Gateway HTTP API (payload 2.0)."""
    return {
        "routeKey": route_key,
        "body": json.dumps(cuerpo) if cuerpo is not None else None,
        "headers": {"authorization": "Bearer %s" % token} if token else {},
        "pathParameters": ruta or {},
        "queryStringParameters": consulta,
    }


def cuerpo(respuesta):
    """Devuelve el JSON de la respuesta de una Lambda."""
    return json.loads(respuesta["body"])


# =========================================================== fixtures
@pytest.fixture(autouse=True)
def tablas_limpias():
    """Vacia las tres tablas antes de cada prueba para que no se contaminen."""
    recurso = boto3.resource("dynamodb", region_name=REGION)
    for nombre, llaves in (
        (TABLA_USUARIOS, ("userId",)),
        (TABLA_REPORTES, ("reportId",)),
        (TABLA_INTERACCIONES, ("reportId", "sk")),
        (TABLA_NOTIFICACIONES, ("userId", "sk")),
        (TABLA_ACTIVIDAD, ("dia", "sk")),
    ):
        tabla = recurso.Table(nombre)
        with tabla.batch_writer() as lote:
            for item in tabla.scan().get("Items", []):
                lote.delete_item(Key={k: item[k] for k in llaves})
    yield


@pytest.fixture
def ciudadano():
    """Registra un ciudadano y devuelve su token y sus datos."""
    def _crear(correo="ciudadano@ejemplo.com", nombre="Ciudadano Prueba"):
        resp = handler_auth.handler(evento("POST /auth/registro", {
            "nombre": nombre, "email": correo, "password": "Prueba12345",
        }), None)
        assert resp["statusCode"] == 201, resp["body"]
        return cuerpo(resp)
    return _crear


@pytest.fixture
def municipio():
    """Siembra la cuenta municipal y devuelve su token."""
    boto3.resource("dynamodb", region_name=REGION).Table(TABLA_USUARIOS).put_item(Item={
        "userId": "usr_municipio",
        "email": "municipio@ejemplo.com",
        "nombre": "Cuenta municipal",
        "rol": "municipio",
        "passwordHash": common.hash_password("Municipio2026"),
        "creadoEn": common.ahora(),
    })
    resp = handler_auth.handler(evento("POST /auth/login", {
        "email": "municipio@ejemplo.com", "password": "Municipio2026",
    }), None)
    assert resp["statusCode"] == 200, resp["body"]
    return cuerpo(resp)["token"]


@pytest.fixture
def reporte(ciudadano):
    """Crea un reporte y devuelve (token_del_autor, datos_del_reporte)."""
    sesion = ciudadano()
    resp = handler_reportes.handler(evento("POST /reportes", {
        "titulo": "Bache sobre Av. Hidalgo",
        "categoria": "Bache",
        "descripcion": "Bache profundo frente al numero 240",
        "direccion": "Av. Hidalgo 240",
        "lat": 20.6736, "lng": -103.344,
    }, token=sesion["token"]), None)
    assert resp["statusCode"] == 201, resp["body"]
    return sesion["token"], cuerpo(resp)["reporte"]
