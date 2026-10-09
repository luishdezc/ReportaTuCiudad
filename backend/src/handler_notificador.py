"""Consumidor de SQS: arma el mensaje y lo publica en SNS (notificacion al ciudadano)."""
import json
import os

import boto3

TOPICO_SNS = os.environ.get("TOPICO_SNS", "")
URL_FRONTEND = os.environ.get("URL_FRONTEND", "")
sns = boto3.client("sns")

PLANTILLAS = {
    "reporte.creado": (
        "Recibimos tu reporte: {titulo}",
        "Hola,\n\nTu reporte \"{titulo}\" ({categoria}) fue recibido con el folio {reportId} "
        "y ya aparece en el mapa publico de ReportaTuCiudad.\n\n"
        "Te avisaremos por este medio cada vez que cambie de estado.\n\n{enlace}"
    ),
    "reporte.estado": (
        "Tu reporte cambio a: {estado}",
        "Hola,\n\nEl reporte \"{titulo}\" (folio {reportId}) ahora esta en estado: {estado}.\n\n"
        "Mensaje de la cuenta municipal: {respuesta}\n{evidencia_texto}\n"
        "Si el estado es Resuelto, entra a la plataforma y confirmanos si el problema realmente "
        "quedo solucionado.\n\n{enlace}"
    ),
    "reporte.reabierto": (
        "Reabrimos el reporte: {titulo}",
        "Hola,\n\nVarios ciudadanos indicaron que el problema del reporte \"{titulo}\" "
        "(folio {reportId}) continua, por lo que volvio al estado {estado}.\n\n{enlace}"
    ),
}


def handler(evento, contexto):  # noqa: ARG001
    procesados, fallidos = 0, []
    for registro in evento.get("Records", []):
        try:
            mensaje = json.loads(registro["body"])
            _notificar(mensaje)
            procesados += 1
        except Exception as exc:  # noqa: BLE001
            print("ERROR al procesar mensaje:", repr(exc), registro.get("body"))
            fallidos.append({"itemIdentifier": registro["messageId"]})
    print("Eventos procesados: %s | fallidos: %s" % (procesados, len(fallidos)))
    # Reintento parcial: solo vuelven a la cola los mensajes que fallaron.
    return {"batchItemFailures": fallidos}


def _notificar(mensaje):
    tipo = mensaje.get("tipo", "")
    datos = dict(mensaje.get("datos", {}))
    asunto_base, cuerpo_base = PLANTILLAS.get(tipo, ("Actualizacion de tu reporte", "{titulo}"))

    datos.setdefault("categoria", "")
    datos.setdefault("respuesta", "(sin comentarios)")
    datos.setdefault("estado", "")
    datos["enlace"] = "Consulta el detalle en: %s" % URL_FRONTEND if URL_FRONTEND else ""
    datos["evidencia_texto"] = (
        "Evidencia de la solucion: %s\n" % datos["evidencia"] if datos.get("evidencia") else ""
    )
    destinatarios = datos.get("destinatarios", [])
    cuerpo = cuerpo_base.format(**datos)
    if destinatarios:
        cuerpo += "\n\nCiudadanos notificados: %s" % ", ".join(destinatarios)

    sns.publish(
        TopicArn=TOPICO_SNS,
        Subject=("ReportaTuCiudad | " + asunto_base.format(**datos))[:99],
        Message=cuerpo,
        MessageAttributes={
            "tipo": {"DataType": "String", "StringValue": tipo or "desconocido"},
            "reportId": {"DataType": "String", "StringValue": str(datos.get("reportId", "-"))},
        },
    )
