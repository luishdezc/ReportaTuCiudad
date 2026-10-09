"""Lambda de usuarios y sesion: registro, login y perfil."""
from boto3.dynamodb.conditions import Key

import common as c


def registrar(evento):
    datos = c.cuerpo_json(evento)
    c.requerido(datos, "nombre", "email", "password")
    email = datos["email"].strip().lower()
    if len(datos["password"]) < 8:
        raise c.ErrorHttp(400, "La contrasena debe tener al menos 8 caracteres")

    existentes = c.usuarios.query(
        IndexName="email-index",
        KeyConditionExpression=Key("email").eq(email),
        Limit=1,
    ).get("Items", [])
    if existentes:
        raise c.ErrorHttp(409, "Ya existe una cuenta con ese correo")

    usuario = {
        "userId": c.nuevo_id("usr"),
        "email": email,
        "nombre": datos["nombre"].strip(),
        "colonia": datos.get("colonia", "").strip(),
        "rol": "ciudadano",
        "passwordHash": c.hash_password(datos["password"]),
        "creadoEn": c.ahora(),
    }
    c.usuarios.put_item(Item=usuario)
    return c.respuesta(201, {"token": c.crear_token(usuario), "usuario": _publico(usuario)})


def iniciar_sesion(evento):
    datos = c.cuerpo_json(evento)
    c.requerido(datos, "email", "password")
    email = datos["email"].strip().lower()
    encontrados = c.usuarios.query(
        IndexName="email-index",
        KeyConditionExpression=Key("email").eq(email),
        Limit=1,
    ).get("Items", [])
    if not encontrados or not c.verificar_password(datos["password"], encontrados[0]["passwordHash"]):
        raise c.ErrorHttp(401, "Correo o contrasena incorrectos")
    usuario = encontrados[0]
    return c.respuesta(200, {"token": c.crear_token(usuario), "usuario": _publico(usuario)})


def perfil(evento):
    sesion = c.usuario_actual(evento)
    item = c.usuarios.get_item(Key={"userId": sesion["sub"]}).get("Item")
    if not item:
        raise c.ErrorHttp(404, "El usuario ya no existe")
    return c.respuesta(200, {"usuario": _publico(item)})


def _publico(usuario):
    return {
        "userId": usuario["userId"],
        "nombre": usuario["nombre"],
        "email": usuario["email"],
        "colonia": usuario.get("colonia", ""),
        "rol": usuario.get("rol", "ciudadano"),
    }


RUTAS = {
    "POST /auth/registro": registrar,
    "POST /auth/login": iniciar_sesion,
    "GET /auth/perfil": perfil,
}


def handler(evento, contexto):  # noqa: ARG001
    return c.enrutar(evento, RUTAS)
