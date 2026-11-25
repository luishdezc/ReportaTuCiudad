"""Pruebas del panel de la cuenta municipal simulada."""
import handler_admin
import handler_interacciones
import handler_reportes
from conftest import cuerpo, evento

ESTADOS = ["Reportado", "En revisión", "Asignado", "En proceso", "Resuelto"]


def _cambiar(report_id, token, estado, respuesta="Avance", evidencia=None):
    datos = {"estado": estado, "respuesta": respuesta}
    if evidencia:
        datos["evidenciaKey"] = evidencia
    return handler_admin.handler(evento(
        "PATCH /admin/reportes/{id}/estado", datos, token=token, ruta={"id": report_id}), None)


# --------------------------------------------------------------- permisos
def test_la_bandeja_requiere_sesion():
    assert handler_admin.handler(evento("GET /admin/reportes"), None)["statusCode"] == 401


def test_un_ciudadano_no_entra_a_la_bandeja(ciudadano):
    sesion = ciudadano()
    resp = handler_admin.handler(evento("GET /admin/reportes", token=sesion["token"]), None)
    assert resp["statusCode"] == 403


def test_un_ciudadano_no_puede_cambiar_estados(reporte):
    token_autor, datos = reporte
    assert _cambiar(datos["reportId"], token_autor, "Resuelto")["statusCode"] == 403


def test_un_ciudadano_no_puede_pedir_url_de_evidencia(ciudadano):
    sesion = ciudadano()
    resp = handler_admin.handler(evento(
        "POST /admin/evidencias", {"contentType": "image/jpeg"}, token=sesion["token"]), None)
    assert resp["statusCode"] == 403


# --------------------------------------------------------------- bandeja
def test_la_bandeja_resume_por_estado(reporte, municipio):
    _, datos = reporte
    resp = handler_admin.handler(evento("GET /admin/reportes", token=municipio), None)
    assert resp["statusCode"] == 200
    bandeja = cuerpo(resp)
    assert bandeja["total"] == 1
    assert bandeja["resumen"]["Reportado"] == 1
    assert bandeja["resumen"]["Resuelto"] == 0
    assert bandeja["reportes"][0]["reportId"] == datos["reportId"]


def test_la_bandeja_ordena_por_numero_de_confirmaciones(municipio, ciudadano):
    autor = ciudadano("autor@ejemplo.com")
    folios = []
    for titulo in ("Poco visto", "Muy visto"):
        resp = handler_reportes.handler(evento("POST /reportes", {
            "titulo": titulo, "categoria": "Bache", "descripcion": "x",
            "lat": 20.0, "lng": -103.0,
        }, token=autor["token"]), None)
        folios.append(cuerpo(resp)["reporte"]["reportId"])

    for correo in ("v1@ejemplo.com", "v2@ejemplo.com"):
        vecina = ciudadano(correo)
        handler_interacciones.handler(evento(
            "POST /reportes/{id}/confirmaciones", {},
            token=vecina["token"], ruta={"id": folios[1]}), None)

    bandeja = cuerpo(handler_admin.handler(
        evento("GET /admin/reportes", token=municipio), None))
    assert bandeja["reportes"][0]["titulo"] == "Muy visto"
    assert bandeja["reportes"][0]["confirmaciones"] == 2


def test_la_bandeja_filtra_por_estado(reporte, municipio):
    resp = handler_admin.handler(evento(
        "GET /admin/reportes", token=municipio, consulta={"estado": "Resuelto"}), None)
    assert cuerpo(resp)["total"] == 0


# --------------------------------------------------------- cambio de estado
def test_recorrer_todos_los_estados(reporte, municipio):
    _, datos = reporte
    for estado in ESTADOS[1:-1]:
        resp = _cambiar(datos["reportId"], municipio, estado)
        assert resp["statusCode"] == 200, resp["body"]
        assert cuerpo(resp)["estado"] == estado

    assert _cambiar(datos["reportId"], municipio, "Resuelto",
                    evidencia="evidencias/foto.jpg")["statusCode"] == 200

    detalle = cuerpo(handler_reportes.handler(
        evento("GET /reportes/{id}", ruta={"id": datos["reportId"]}), None))
    assert detalle["reporte"]["estado"] == "Resuelto"
    assert detalle["reporte"]["evidencia"].endswith("evidencias/foto.jpg")
    # el inicial mas los cuatro cambios
    assert len(detalle["historial"]) == 5


def test_un_estado_que_no_existe(reporte, municipio):
    _, datos = reporte
    resp = _cambiar(datos["reportId"], municipio, "Archivado")
    assert resp["statusCode"] == 400
    assert "Reportado" in cuerpo(resp)["error"]


def test_cerrar_sin_evidencia_se_rechaza(reporte, municipio):
    _, datos = reporte
    resp = _cambiar(datos["reportId"], municipio, "Resuelto")
    assert resp["statusCode"] == 400
    assert "evidencia" in cuerpo(resp)["error"].lower()


def test_cambiar_el_estado_de_un_reporte_inexistente(municipio):
    assert _cambiar("rep_noexiste", municipio, "Asignado")["statusCode"] == 404


def test_la_respuesta_municipal_queda_en_el_detalle(reporte, municipio):
    _, datos = reporte
    _cambiar(datos["reportId"], municipio, "Asignado", respuesta="Cuadrilla el jueves")
    detalle = cuerpo(handler_reportes.handler(
        evento("GET /reportes/{id}", ruta={"id": datos["reportId"]}), None))
    assert detalle["reporte"]["respuestaMunicipal"] == "Cuadrilla el jueves"
    assert detalle["historial"][-1]["mensaje"] == "Cuadrilla el jueves"


def test_url_prefirmada_de_evidencia(municipio):
    resp = handler_admin.handler(evento(
        "POST /admin/evidencias", {"contentType": "image/png"}, token=municipio), None)
    assert resp["statusCode"] == 200
    assert cuerpo(resp)["key"].startswith("evidencias/")
    assert cuerpo(resp)["key"].endswith(".png")
