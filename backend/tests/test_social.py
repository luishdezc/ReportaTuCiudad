"""Pruebas de la capa comunitaria: perfiles, feed, estadisticas y avisos."""
import handler_admin
import handler_interacciones
import handler_reportes
import handler_social
from conftest import cuerpo, evento


def _crear(token, titulo, categoria="Bache"):
    resp = handler_reportes.handler(evento("POST /reportes", {
        "titulo": titulo, "categoria": categoria, "descripcion": "x",
        "direccion": "Calle 1", "lat": 20.67, "lng": -103.34,
    }, token=token), None)
    assert resp["statusCode"] == 201, resp["body"]
    return cuerpo(resp)["reporte"]


# ============================================================ perfil publico
def test_el_perfil_resume_lo_que_aporto_el_ciudadano(ciudadano):
    sesion = ciudadano("ana@ejemplo.com", "Ana Vecina")
    _crear(sesion["token"], "Bache uno")
    _crear(sesion["token"], "Bache dos")

    resp = handler_social.handler(evento(
        "GET /usuarios/{id}/perfil", ruta={"id": sesion["usuario"]["userId"]}), None)
    assert resp["statusCode"] == 200
    datos = cuerpo(resp)
    assert datos["usuario"]["nombre"] == "Ana Vecina"
    assert datos["estadisticas"]["reportes"] == 2
    assert datos["estadisticas"]["resueltos"] == 0
    assert len(datos["reportes"]) == 2


def test_el_perfil_es_publico(ciudadano):
    sesion = ciudadano("publica@ejemplo.com")
    resp = handler_social.handler(evento(
        "GET /usuarios/{id}/perfil", ruta={"id": sesion["usuario"]["userId"]}), None)
    assert resp["statusCode"] == 200  # sin token


def test_perfil_de_alguien_que_no_existe():
    resp = handler_social.handler(
        evento("GET /usuarios/{id}/perfil", ruta={"id": "usr_fantasma"}), None)
    assert resp["statusCode"] == 404


def test_las_insignias_se_ganan_al_cruzar_el_umbral(ciudadano):
    sesion = ciudadano("insignias@ejemplo.com")
    _crear(sesion["token"], "Primero")

    def insignia(datos, clave):
        return next(i for i in datos["insignias"] if i["clave"] == clave)

    datos = cuerpo(handler_social.handler(evento(
        "GET /usuarios/{id}/perfil", ruta={"id": sesion["usuario"]["userId"]}), None))
    assert insignia(datos, "primer_reporte")["obtenida"] is True
    assert insignia(datos, "vigilante")["obtenida"] is False
    assert insignia(datos, "vigilante")["avance"] == 1

    for n in range(4):
        _crear(sesion["token"], "Reporte %d" % n)

    datos = cuerpo(handler_social.handler(evento(
        "GET /usuarios/{id}/perfil", ruta={"id": sesion["usuario"]["userId"]}), None))
    assert insignia(datos, "vigilante")["obtenida"] is True


def test_el_perfil_cuenta_las_confirmaciones_dadas(reporte, ciudadano):
    _, datos = reporte
    vecina = ciudadano("confirmadora@ejemplo.com")
    handler_interacciones.handler(evento(
        "POST /reportes/{id}/confirmaciones", {},
        token=vecina["token"], ruta={"id": datos["reportId"]}), None)

    perfil = cuerpo(handler_social.handler(evento(
        "GET /usuarios/{id}/perfil", ruta={"id": vecina["usuario"]["userId"]}), None))
    assert perfil["estadisticas"]["confirmaciones"] == 1


# ================================================================ seguidores
def test_seguir_y_dejar_de_seguir(reporte, ciudadano):
    _, datos = reporte
    vecina = ciudadano("seguidora@ejemplo.com")
    ruta = {"id": datos["reportId"]}

    resp = handler_interacciones.handler(evento(
        "POST /reportes/{id}/seguidores", {}, token=vecina["token"], ruta=ruta), None)
    assert resp["statusCode"] == 200
    assert cuerpo(resp) == {"siguiendo": True, "seguidores": 1, "titulo": datos["titulo"]}

    detalle = cuerpo(handler_reportes.handler(
        evento("GET /reportes/{id}", ruta=ruta), None))
    assert vecina["usuario"]["userId"] in detalle["seguidores"]

    resp = handler_interacciones.handler(evento(
        "DELETE /reportes/{id}/seguidores", {}, token=vecina["token"], ruta=ruta), None)
    assert cuerpo(resp) == {"siguiendo": False, "seguidores": 0}


def test_no_se_puede_seguir_dos_veces(reporte, ciudadano):
    _, datos = reporte
    vecina = ciudadano("doble@ejemplo.com")
    ev = evento("POST /reportes/{id}/seguidores", {},
                token=vecina["token"], ruta={"id": datos["reportId"]})
    assert handler_interacciones.handler(ev, None)["statusCode"] == 200
    assert handler_interacciones.handler(ev, None)["statusCode"] == 409


def test_dejar_de_seguir_algo_que_no_sigues(reporte, ciudadano):
    _, datos = reporte
    vecina = ciudadano("nada@ejemplo.com")
    resp = handler_interacciones.handler(evento(
        "DELETE /reportes/{id}/seguidores", {},
        token=vecina["token"], ruta={"id": datos["reportId"]}), None)
    assert resp["statusCode"] == 409


def test_seguir_requiere_sesion(reporte):
    _, datos = reporte
    resp = handler_interacciones.handler(evento(
        "POST /reportes/{id}/seguidores", {}, ruta={"id": datos["reportId"]}), None)
    assert resp["statusCode"] == 401


# ================================================================ actividad
def test_el_feed_registra_el_alta_de_un_reporte(ciudadano):
    sesion = ciudadano("feed@ejemplo.com", "Feed Vecino")
    _crear(sesion["token"], "Bache del feed")

    eventos = cuerpo(handler_social.handler(evento("GET /actividad"), None))["eventos"]
    assert any(e["tipo"] == "reporte.creado" and e["titulo"] == "Bache del feed"
               for e in eventos)


def test_el_feed_registra_los_cambios_de_estado(reporte, municipio):
    _, datos = reporte
    handler_admin.handler(evento(
        "PATCH /admin/reportes/{id}/estado", {"estado": "Asignado", "respuesta": "Cuadrilla lista"},
        token=municipio, ruta={"id": datos["reportId"]}), None)

    eventos = cuerpo(handler_social.handler(evento("GET /actividad"), None))["eventos"]
    cambio = next(e for e in eventos if e["tipo"] == "reporte.estado")
    assert cambio["estado"] == "Asignado"
    assert cambio["detalle"] == "Cuadrilla lista"


def test_el_feed_viene_del_mas_nuevo_al_mas_viejo(ciudadano):
    sesion = ciudadano("orden@ejemplo.com")
    _crear(sesion["token"], "El primero")
    _crear(sesion["token"], "El segundo")

    eventos = cuerpo(handler_social.handler(evento("GET /actividad"), None))["eventos"]
    titulos = [e["titulo"] for e in eventos if e["tipo"] == "reporte.creado"]
    assert titulos[0] == "El segundo"


def test_el_feed_es_publico():
    assert handler_social.handler(evento("GET /actividad"), None)["statusCode"] == 200


# ============================================================= estadisticas
def test_las_estadisticas_cuentan_altas_y_cierres(reporte, municipio):
    _, datos = reporte
    antes = cuerpo(handler_social.handler(evento("GET /estadisticas"), None))
    assert antes["reportesCreados"] >= 1

    handler_admin.handler(evento(
        "PATCH /admin/reportes/{id}/estado",
        {"estado": "Resuelto", "respuesta": "Listo", "evidenciaKey": "evidencias/x.jpg"},
        token=municipio, ruta={"id": datos["reportId"]}), None)

    despues = cuerpo(handler_social.handler(evento("GET /estadisticas"), None))
    assert despues["reportesResueltos"] == antes["reportesResueltos"] + 1
    assert despues["porcentajeResuelto"] > 0


def test_las_estadisticas_desglosan_por_categoria(ciudadano):
    sesion = ciudadano("categorias@ejemplo.com")
    _crear(sesion["token"], "Una fuga", categoria="Fuga de agua")

    datos = cuerpo(handler_social.handler(evento("GET /estadisticas"), None))
    assert datos["porCategoria"].get("Fuga de agua") == 1


def test_las_estadisticas_con_la_ciudad_vacia():
    datos = cuerpo(handler_social.handler(evento("GET /estadisticas"), None))
    assert datos["reportesCreados"] == 0
    assert datos["porcentajeResuelto"] == 0
    assert datos["horasPromedioResolucion"] == 0


# ============================================================ notificaciones
def test_confirmar_deja_un_aviso_al_autor(reporte, ciudadano):
    token_autor, datos = reporte
    vecina = ciudadano("avisadora@ejemplo.com", "Vecina Avisadora")
    handler_interacciones.handler(evento(
        "POST /reportes/{id}/confirmaciones", {},
        token=vecina["token"], ruta={"id": datos["reportId"]}), None)

    avisos = cuerpo(handler_social.handler(
        evento("GET /notificaciones", token=token_autor), None))
    assert avisos["sinLeer"] == 1
    assert "Vecina Avisadora" in avisos["notificaciones"][0]["cuerpo"]
    assert avisos["notificaciones"][0]["reportId"] == datos["reportId"]


def test_el_cambio_de_estado_avisa_a_quien_sigue(reporte, municipio, ciudadano):
    _, datos = reporte
    vecina = ciudadano("interesada@ejemplo.com")
    handler_interacciones.handler(evento(
        "POST /reportes/{id}/seguidores", {},
        token=vecina["token"], ruta={"id": datos["reportId"]}), None)

    handler_admin.handler(evento(
        "PATCH /admin/reportes/{id}/estado", {"estado": "En proceso", "respuesta": "Ya vamos"},
        token=municipio, ruta={"id": datos["reportId"]}), None)

    avisos = cuerpo(handler_social.handler(
        evento("GET /notificaciones", token=vecina["token"]), None))
    assert avisos["sinLeer"] == 1
    assert "En proceso" in avisos["notificaciones"][0]["titulo"]


def test_quien_comenta_no_se_avisa_a_si_mismo(reporte, ciudadano):
    _, datos = reporte
    vecina = ciudadano("comentarista2@ejemplo.com")
    handler_interacciones.handler(evento(
        "POST /reportes/{id}/comentarios", {"texto": "Confirmo"},
        token=vecina["token"], ruta={"id": datos["reportId"]}), None)

    avisos = cuerpo(handler_social.handler(
        evento("GET /notificaciones", token=vecina["token"]), None))
    assert avisos["sinLeer"] == 0


def test_marcar_los_avisos_como_leidos(reporte, ciudadano):
    token_autor, datos = reporte
    vecina = ciudadano("marcadora@ejemplo.com")
    handler_interacciones.handler(evento(
        "POST /reportes/{id}/confirmaciones", {},
        token=vecina["token"], ruta={"id": datos["reportId"]}), None)

    resp = handler_social.handler(evento("POST /notificaciones/leidas", {}, token=token_autor), None)
    assert cuerpo(resp)["marcadas"] == 1

    avisos = cuerpo(handler_social.handler(
        evento("GET /notificaciones", token=token_autor), None))
    assert avisos["sinLeer"] == 0
    assert avisos["notificaciones"][0]["leida"] is True


def test_los_avisos_requieren_sesion():
    assert handler_social.handler(evento("GET /notificaciones"), None)["statusCode"] == 401
    assert handler_social.handler(evento("POST /notificaciones/leidas", {}), None)["statusCode"] == 401


def test_cada_quien_ve_solo_sus_avisos(reporte, ciudadano):
    _, datos = reporte
    vecina = ciudadano("ajena@ejemplo.com")
    otra = ciudadano("otra@ejemplo.com")
    handler_interacciones.handler(evento(
        "POST /reportes/{id}/confirmaciones", {},
        token=vecina["token"], ruta={"id": datos["reportId"]}), None)

    avisos = cuerpo(handler_social.handler(
        evento("GET /notificaciones", token=otra["token"]), None))
    assert avisos["notificaciones"] == []


# ================================================================ metricas
def test_crear_un_reporte_publica_su_metrica(ciudadano, capsys):
    import json
    sesion = ciudadano("metrica@ejemplo.com")
    _crear(sesion["token"], "Con metrica", categoria="Semáforo dañado")

    emitidas = []
    for linea in capsys.readouterr().out.split("\n"):
        if linea.startswith("{") and "_aws" in linea:
            emitidas.append(json.loads(linea))

    creados = next(m for m in emitidas if "ReportesCreados" in m)
    assert creados["ReportesCreados"] == 1
    assert creados["Categoria"] == "Semáforo dañado"
    # un juego de dimensiones para el total y otro para el desglose
    juegos = creados["_aws"]["CloudWatchMetrics"][0]["Dimensions"]
    assert ["Ambiente"] in juegos
    assert any("Categoria" in j for j in juegos)
