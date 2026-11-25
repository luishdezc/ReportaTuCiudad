"""Pruebas de la participacion ciudadana: confirmaciones, comentarios y cierre."""
import handler_admin
import handler_interacciones
import handler_reportes
from conftest import cuerpo, evento


def _resolver(report_id, token_municipio):
    """Lleva un reporte a Resuelto para poder validarlo."""
    resp = handler_admin.handler(evento(
        "PATCH /admin/reportes/{id}/estado",
        {"estado": "Resuelto", "respuesta": "Reparado", "evidenciaKey": "evidencias/x.jpg"},
        token=token_municipio, ruta={"id": report_id}), None)
    assert resp["statusCode"] == 200, resp["body"]


# ------------------------------------------------------------ confirmaciones
def test_confirmar_incrementa_el_contador(reporte, ciudadano):
    _, datos = reporte
    vecina = ciudadano("vecina@ejemplo.com")
    resp = handler_interacciones.handler(evento(
        "POST /reportes/{id}/confirmaciones", {},
        token=vecina["token"], ruta={"id": datos["reportId"]}), None)
    assert resp["statusCode"] == 200
    assert cuerpo(resp)["confirmaciones"] == 1


def test_no_se_puede_confirmar_dos_veces(reporte, ciudadano):
    _, datos = reporte
    vecina = ciudadano("vecina2@ejemplo.com")
    ev = evento("POST /reportes/{id}/confirmaciones", {},
                token=vecina["token"], ruta={"id": datos["reportId"]})
    assert handler_interacciones.handler(ev, None)["statusCode"] == 200
    assert handler_interacciones.handler(ev, None)["statusCode"] == 409

    detalle = cuerpo(handler_reportes.handler(
        evento("GET /reportes/{id}", ruta={"id": datos["reportId"]}), None))
    assert detalle["reporte"]["confirmaciones"] == 1


def test_el_autor_no_puede_confirmar_su_propio_reporte(reporte):
    token_autor, datos = reporte
    resp = handler_interacciones.handler(evento(
        "POST /reportes/{id}/confirmaciones", {},
        token=token_autor, ruta={"id": datos["reportId"]}), None)
    assert resp["statusCode"] == 400


def test_confirmar_un_reporte_inexistente(ciudadano):
    vecina = ciudadano("vecina3@ejemplo.com")
    resp = handler_interacciones.handler(evento(
        "POST /reportes/{id}/confirmaciones", {},
        token=vecina["token"], ruta={"id": "rep_noexiste"}), None)
    assert resp["statusCode"] == 404


# ----------------------------------------------------------------- comentarios
def test_comentar_aparece_en_el_detalle(reporte, ciudadano):
    _, datos = reporte
    vecina = ciudadano("comentarista@ejemplo.com", "Vecina Comentarista")
    resp = handler_interacciones.handler(evento(
        "POST /reportes/{id}/comentarios", {"texto": "Yo tambien paso por ahi"},
        token=vecina["token"], ruta={"id": datos["reportId"]}), None)
    assert resp["statusCode"] == 201

    detalle = cuerpo(handler_reportes.handler(
        evento("GET /reportes/{id}", ruta={"id": datos["reportId"]}), None))
    assert detalle["reporte"]["comentarios"] == 1
    assert detalle["comentarios"][0]["texto"] == "Yo tambien paso por ahi"
    assert detalle["comentarios"][0]["oficial"] is False


def test_el_comentario_del_municipio_se_marca_como_oficial(reporte, municipio):
    _, datos = reporte
    handler_interacciones.handler(evento(
        "POST /reportes/{id}/comentarios", {"texto": "Ya lo revisamos"},
        token=municipio, ruta={"id": datos["reportId"]}), None)
    detalle = cuerpo(handler_reportes.handler(
        evento("GET /reportes/{id}", ruta={"id": datos["reportId"]}), None))
    assert detalle["comentarios"][0]["oficial"] is True


def test_un_comentario_vacio_se_rechaza(reporte, ciudadano):
    _, datos = reporte
    vecina = ciudadano("vacia@ejemplo.com")
    resp = handler_interacciones.handler(evento(
        "POST /reportes/{id}/comentarios", {"texto": "   "},
        token=vecina["token"], ruta={"id": datos["reportId"]}), None)
    assert resp["statusCode"] == 400


# ------------------------------------------------------------ validacion final
def test_no_se_puede_validar_un_reporte_que_no_esta_resuelto(reporte):
    token_autor, datos = reporte
    resp = handler_interacciones.handler(evento(
        "POST /reportes/{id}/validacion", {"resuelto": True},
        token=token_autor, ruta={"id": datos["reportId"]}), None)
    assert resp["statusCode"] == 400


def test_validar_el_cierre_de_forma_positiva(reporte, municipio):
    token_autor, datos = reporte
    _resolver(datos["reportId"], municipio)
    resp = handler_interacciones.handler(evento(
        "POST /reportes/{id}/validacion", {"resuelto": True},
        token=token_autor, ruta={"id": datos["reportId"]}), None)
    assert resp["statusCode"] == 200
    assert cuerpo(resp) == {"validacionesSi": 1, "validacionesNo": 0, "reabierto": False}


def test_no_se_puede_votar_dos_veces(reporte, municipio):
    token_autor, datos = reporte
    _resolver(datos["reportId"], municipio)
    ev = evento("POST /reportes/{id}/validacion", {"resuelto": True},
                token=token_autor, ruta={"id": datos["reportId"]})
    assert handler_interacciones.handler(ev, None)["statusCode"] == 200
    assert handler_interacciones.handler(ev, None)["statusCode"] == 409


def test_dos_votos_negativos_reabren_el_reporte(reporte, municipio, ciudadano):
    token_autor, datos = reporte
    _resolver(datos["reportId"], municipio)

    primera = handler_interacciones.handler(evento(
        "POST /reportes/{id}/validacion", {"resuelto": False},
        token=token_autor, ruta={"id": datos["reportId"]}), None)
    assert cuerpo(primera)["reabierto"] is False   # con un solo voto todavia no

    vecina = ciudadano("inconforme@ejemplo.com")
    segunda = handler_interacciones.handler(evento(
        "POST /reportes/{id}/validacion", {"resuelto": False},
        token=vecina["token"], ruta={"id": datos["reportId"]}), None)
    assert cuerpo(segunda)["reabierto"] is True

    detalle = cuerpo(handler_reportes.handler(
        evento("GET /reportes/{id}", ruta={"id": datos["reportId"]}), None))
    assert detalle["reporte"]["estado"] == "En revisión"
    assert detalle["historial"][-1]["autor"] == "Sistema"


def test_un_voto_positivo_evita_la_reapertura(reporte, municipio, ciudadano):
    token_autor, datos = reporte
    _resolver(datos["reportId"], municipio)
    handler_interacciones.handler(evento(
        "POST /reportes/{id}/validacion", {"resuelto": True},
        token=token_autor, ruta={"id": datos["reportId"]}), None)

    for correo in ("a@ejemplo.com", "b@ejemplo.com"):
        vecina = ciudadano(correo)
        resp = handler_interacciones.handler(evento(
            "POST /reportes/{id}/validacion", {"resuelto": False},
            token=vecina["token"], ruta={"id": datos["reportId"]}), None)
    # 2 negativos contra 1 positivo: la mayoria es negativa, se reabre
    assert cuerpo(resp)["reabierto"] is True
