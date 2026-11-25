"""Pruebas del consumidor de SQS que publica las notificaciones en SNS."""
import json

import handler_notificador
import pytest


class SnsFalso:
    """Registra las publicaciones en vez de enviarlas."""

    def __init__(self):
        self.publicaciones = []

    def publish(self, **kwargs):
        self.publicaciones.append(kwargs)
        return {"MessageId": "falso"}


@pytest.fixture
def sns(monkeypatch):
    falso = SnsFalso()
    monkeypatch.setattr(handler_notificador, "sns", falso)
    return falso


def registro(tipo, datos, message_id="m1"):
    return {"messageId": message_id,
            "body": json.dumps({"tipo": tipo, "datos": datos, "fecha": "2026-10-24T12:00:00Z"})}


def test_reporte_creado_arma_asunto_y_cuerpo(sns):
    salida = handler_notificador.handler({"Records": [registro("reporte.creado", {
        "reportId": "rep_abc123", "titulo": "Bache en Hidalgo", "categoria": "Bache",
        "estado": "Reportado", "destinatarios": ["ana@ejemplo.com"],
    })]}, None)

    assert salida == {"batchItemFailures": []}
    assert len(sns.publicaciones) == 1
    envio = sns.publicaciones[0]
    assert "Bache en Hidalgo" in envio["Subject"]
    assert envio["Subject"].startswith("ReportaTuCiudad |")
    assert "rep_abc123" in envio["Message"]
    assert "ana@ejemplo.com" in envio["Message"]
    assert envio["MessageAttributes"]["tipo"]["StringValue"] == "reporte.creado"


def test_el_asunto_nunca_pasa_de_cien_caracteres(sns):
    handler_notificador.handler({"Records": [registro("reporte.creado", {
        "reportId": "rep_1", "titulo": "T" * 300, "categoria": "Bache",
        "estado": "Reportado", "destinatarios": [],
    })]}, None)
    assert len(sns.publicaciones[0]["Subject"]) <= 99


def test_cambio_de_estado_incluye_respuesta_y_evidencia(sns):
    handler_notificador.handler({"Records": [registro("reporte.estado", {
        "reportId": "rep_xyz", "titulo": "Luminaria", "estado": "Resuelto",
        "respuesta": "Lampara sustituida",
        "evidencia": "https://bucket.s3.amazonaws.com/evidencias/x.jpg",
        "destinatarios": ["ana@ejemplo.com", "beto@ejemplo.com"],
    })]}, None)

    mensaje = sns.publicaciones[0]["Message"]
    assert "Resuelto" in sns.publicaciones[0]["Subject"]
    assert "Lampara sustituida" in mensaje
    assert "evidencias/x.jpg" in mensaje
    assert "beto@ejemplo.com" in mensaje


def test_sin_evidencia_no_aparece_esa_linea(sns):
    handler_notificador.handler({"Records": [registro("reporte.estado", {
        "reportId": "rep_xyz", "titulo": "Bache", "estado": "En proceso",
        "respuesta": "Cuadrilla asignada", "destinatarios": [],
    })]}, None)
    assert "Evidencia" not in sns.publicaciones[0]["Message"]


def test_reapertura(sns):
    handler_notificador.handler({"Records": [registro("reporte.reabierto", {
        "reportId": "rep_r", "titulo": "Fuga", "estado": "En revisión",
        "destinatarios": ["ana@ejemplo.com"],
    })]}, None)
    assert "Reabrimos" in sns.publicaciones[0]["Subject"]


def test_un_tipo_desconocido_no_rompe_el_lote(sns):
    salida = handler_notificador.handler({"Records": [registro("tipo.inventado", {
        "reportId": "rep_x", "titulo": "Algo", "destinatarios": [],
    })]}, None)
    assert salida == {"batchItemFailures": []}
    assert len(sns.publicaciones) == 1


def test_un_mensaje_corrupto_se_reporta_para_reintento(sns):
    salida = handler_notificador.handler(
        {"Records": [{"messageId": "malo", "body": "{no es json"}]}, None)
    assert salida == {"batchItemFailures": [{"itemIdentifier": "malo"}]}
    assert sns.publicaciones == []


def test_solo_falla_el_mensaje_malo_del_lote(sns):
    salida = handler_notificador.handler({"Records": [
        registro("reporte.creado", {"reportId": "rep_ok", "titulo": "Bien",
                                    "categoria": "Bache", "estado": "Reportado",
                                    "destinatarios": []}, message_id="bueno"),
        {"messageId": "malo", "body": "{{{"},
    ]}, None)
    assert salida == {"batchItemFailures": [{"itemIdentifier": "malo"}]}
    assert len(sns.publicaciones) == 1   # el bueno si se envio


def test_lote_vacio(sns):
    assert handler_notificador.handler({"Records": []}, None) == {"batchItemFailures": []}
