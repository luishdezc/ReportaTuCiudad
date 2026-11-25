"""Pruebas de la Lambda de usuarios y sesion."""
import handler_auth
from conftest import cuerpo, evento


def test_registro_crea_la_cuenta_y_devuelve_token(ciudadano):
    datos = ciudadano("ana@ejemplo.com", "Ana Vecina")
    assert datos["usuario"]["email"] == "ana@ejemplo.com"
    assert datos["usuario"]["rol"] == "ciudadano"
    assert datos["token"].count(".") == 2          # cabecera.carga.firma
    assert "passwordHash" not in datos["usuario"]  # nunca se expone


def test_el_correo_se_normaliza_a_minusculas(ciudadano):
    datos = ciudadano("Ana.Vecina@Ejemplo.COM")
    assert datos["usuario"]["email"] == "ana.vecina@ejemplo.com"


def test_no_se_permite_registrar_dos_veces_el_mismo_correo(ciudadano):
    ciudadano("repetida@ejemplo.com")
    resp = handler_auth.handler(evento("POST /auth/registro", {
        "nombre": "Otra", "email": "repetida@ejemplo.com", "password": "Prueba12345",
    }), None)
    assert resp["statusCode"] == 409


def test_la_contrasena_debe_tener_al_menos_ocho_caracteres():
    resp = handler_auth.handler(evento("POST /auth/registro", {
        "nombre": "Corta", "email": "corta@ejemplo.com", "password": "1234567",
    }), None)
    assert resp["statusCode"] == 400


def test_faltan_campos_obligatorios():
    resp = handler_auth.handler(evento("POST /auth/registro", {"nombre": "Sin correo"}), None)
    assert resp["statusCode"] == 400
    assert "email" in cuerpo(resp)["error"]


def test_cuerpo_que_no_es_json():
    ev = evento("POST /auth/registro")
    ev["body"] = "{esto no es json"
    assert handler_auth.handler(ev, None)["statusCode"] == 400


def test_login_correcto_devuelve_token(ciudadano):
    ciudadano("beto@ejemplo.com")
    resp = handler_auth.handler(evento("POST /auth/login", {
        "email": "beto@ejemplo.com", "password": "Prueba12345",
    }), None)
    assert resp["statusCode"] == 200
    assert cuerpo(resp)["usuario"]["email"] == "beto@ejemplo.com"


def test_login_con_contrasena_incorrecta(ciudadano):
    ciudadano("carmen@ejemplo.com")
    resp = handler_auth.handler(evento("POST /auth/login", {
        "email": "carmen@ejemplo.com", "password": "equivocada",
    }), None)
    assert resp["statusCode"] == 401


def test_login_de_un_correo_que_no_existe():
    resp = handler_auth.handler(evento("POST /auth/login", {
        "email": "fantasma@ejemplo.com", "password": "Prueba12345",
    }), None)
    assert resp["statusCode"] == 401


def test_perfil_requiere_sesion():
    assert handler_auth.handler(evento("GET /auth/perfil"), None)["statusCode"] == 401


def test_perfil_con_sesion_valida(ciudadano):
    sesion = ciudadano("dani@ejemplo.com", "Dani Peaton")
    resp = handler_auth.handler(evento("GET /auth/perfil", token=sesion["token"]), None)
    assert resp["statusCode"] == 200
    assert cuerpo(resp)["usuario"]["nombre"] == "Dani Peaton"


def test_un_token_alterado_se_rechaza(ciudadano):
    sesion = ciudadano("eva@ejemplo.com")
    cabecera, carga, firma = sesion["token"].split(".")
    alterado = "%s.%s.%s" % (cabecera, carga, firma[:-2] + "xx")
    resp = handler_auth.handler(evento("GET /auth/perfil", token=alterado), None)
    assert resp["statusCode"] == 401


def test_ruta_inexistente():
    assert handler_auth.handler(evento("GET /auth/nada"), None)["statusCode"] == 404
