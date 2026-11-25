"""Pruebas de la Lambda de reportes: alta, mapa y detalle."""
import handler_reportes
from conftest import cuerpo, evento


def test_crear_reporte_lo_deja_en_estado_reportado(reporte):
    _, datos = reporte
    assert datos["estado"] == "Reportado"
    assert datos["reportId"].startswith("rep_")
    assert datos["confirmaciones"] == 0
    assert datos["lat"] == 20.6736


def test_crear_reporte_requiere_sesion():
    resp = handler_reportes.handler(evento("POST /reportes", {
        "titulo": "Sin sesion", "categoria": "Bache", "descripcion": "x",
        "lat": 20.0, "lng": -103.0,
    }), None)
    assert resp["statusCode"] == 401


def test_categoria_invalida(ciudadano):
    sesion = ciudadano()
    resp = handler_reportes.handler(evento("POST /reportes", {
        "titulo": "Categoria rara", "categoria": "Ovni", "descripcion": "x",
        "lat": 20.0, "lng": -103.0,
    }, token=sesion["token"]), None)
    assert resp["statusCode"] == 400


def test_sin_ubicacion_no_se_puede_reportar(ciudadano):
    sesion = ciudadano()
    resp = handler_reportes.handler(evento("POST /reportes", {
        "titulo": "Sin mapa", "categoria": "Bache", "descripcion": "x",
    }, token=sesion["token"]), None)
    assert resp["statusCode"] == 400
    assert "ubicacion" in cuerpo(resp)["error"].lower() or "ubicación" in cuerpo(resp)["error"].lower()


def test_faltan_titulo_o_descripcion(ciudadano):
    sesion = ciudadano()
    resp = handler_reportes.handler(evento("POST /reportes", {
        "categoria": "Bache", "lat": 20.0, "lng": -103.0,
    }, token=sesion["token"]), None)
    assert resp["statusCode"] == 400


def test_el_mapa_publico_no_requiere_sesion(reporte):
    _, datos = reporte
    resp = handler_reportes.handler(evento("GET /reportes"), None)
    assert resp["statusCode"] == 200
    folios = [r["reportId"] for r in cuerpo(resp)["reportes"]]
    assert datos["reportId"] in folios


def test_el_mapa_filtra_por_estado(reporte):
    _, datos = reporte
    resp = handler_reportes.handler(
        evento("GET /reportes", consulta={"estado": "Reportado"}), None)
    assert datos["reportId"] in [r["reportId"] for r in cuerpo(resp)["reportes"]]

    resp = handler_reportes.handler(
        evento("GET /reportes", consulta={"estado": "Resuelto"}), None)
    assert cuerpo(resp)["total"] == 0


def test_el_mapa_filtra_por_categoria(reporte):
    resp = handler_reportes.handler(
        evento("GET /reportes", consulta={"categoria": "Fuga de agua"}), None)
    assert cuerpo(resp)["total"] == 0


def test_el_detalle_trae_el_historial_inicial(reporte):
    _, datos = reporte
    resp = handler_reportes.handler(
        evento("GET /reportes/{id}", ruta={"id": datos["reportId"]}), None)
    assert resp["statusCode"] == 200
    detalle = cuerpo(resp)
    assert detalle["reporte"]["titulo"] == "Bache sobre Av. Hidalgo"
    assert len(detalle["historial"]) == 1
    assert detalle["historial"][0]["estado"] == "Reportado"
    assert detalle["comentarios"] == []


def test_detalle_de_un_reporte_que_no_existe():
    resp = handler_reportes.handler(
        evento("GET /reportes/{id}", ruta={"id": "rep_noexiste"}), None)
    assert resp["statusCode"] == 404


def test_url_prefirmada_para_subir_la_foto(ciudadano):
    sesion = ciudadano()
    resp = handler_reportes.handler(evento(
        "POST /reportes/carga", {"contentType": "image/jpeg"}, token=sesion["token"]), None)
    assert resp["statusCode"] == 200
    datos = cuerpo(resp)
    assert datos["key"].startswith("reportes/")
    assert datos["key"].endswith(".jpg")
    # moto firma con SigV2 y AWS con SigV4; lo estable es que venga firmada y con caducidad
    assert "Signature" in datos["url"] and "Expires" in datos["url"]
    assert datos["key"] in datos["url"]
    assert datos["urlPublica"].endswith(datos["key"])


def test_solo_se_aceptan_imagenes(ciudadano):
    sesion = ciudadano()
    resp = handler_reportes.handler(evento(
        "POST /reportes/carga", {"contentType": "application/pdf"}, token=sesion["token"]), None)
    assert resp["statusCode"] == 400
