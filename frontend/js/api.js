/* Cliente del API de ReportaTuCiudad y manejo de la sesión en el navegador.
   No depende de Vue: lo usan tanto el mapa ciudadano como el panel municipal. */

const API = {
  base() {
    return ((window.CONFIG && window.CONFIG.API_URL) || "").replace(/\/$/, "");
  },

  token() {
    return localStorage.getItem("rtc_token");
  },

  usuario() {
    try {
      return JSON.parse(localStorage.getItem("rtc_usuario") || "null");
    } catch (e) {
      return null;
    }
  },

  guardarSesion(token, usuario) {
    localStorage.setItem("rtc_token", token);
    localStorage.setItem("rtc_usuario", JSON.stringify(usuario));
  },

  cerrarSesion() {
    localStorage.removeItem("rtc_token");
    localStorage.removeItem("rtc_usuario");
  },

  async peticion(metodo, ruta, cuerpo) {
    const cabeceras = { "Content-Type": "application/json" };
    if (this.token()) cabeceras["Authorization"] = "Bearer " + this.token();

    let respuesta;
    try {
      respuesta = await fetch(this.base() + ruta, {
        method: metodo,
        headers: cabeceras,
        body: cuerpo ? JSON.stringify(cuerpo) : undefined,
      });
    } catch (e) {
      throw new Error("No se pudo conectar con el servidor. Revisa tu conexión.");
    }

    const texto = await respuesta.text();
    let datos = {};
    if (texto) {
      try {
        datos = JSON.parse(texto);
      } catch (e) {
        throw new Error("El servidor respondió algo que no se pudo leer.");
      }
    }
    if (!respuesta.ok) throw new Error(datos.error || "Error " + respuesta.status);
    return datos;
  },

  get(ruta) { return this.peticion("GET", ruta); },
  post(ruta, cuerpo) { return this.peticion("POST", ruta, cuerpo); },
  patch(ruta, cuerpo) { return this.peticion("PATCH", ruta, cuerpo); },

  /* Sube la imagen directo a S3 con una URL prefirmada y devuelve su key. */
  async subirImagen(archivo, ruta) {
    if (!archivo) return "";
    if (archivo.size > 8 * 1024 * 1024) {
      throw new Error("La imagen pesa más de 8 MB. Usa una más ligera.");
    }
    const permiso = await this.post(ruta, { contentType: archivo.type });
    const carga = await fetch(permiso.url, {
      method: "PUT",
      headers: { "Content-Type": archivo.type },
      body: archivo,
    });
    if (!carga.ok) throw new Error("No se pudo subir la imagen.");
    return permiso.key;
  },
};

const ESTADOS = ["Reportado", "En revisión", "Asignado", "En proceso", "Resuelto"];

const CATEGORIAS = [
  "Bache",
  "Luminaria dañada",
  "Acumulación de basura",
  "Fuga de agua",
  "Árbol caído",
  "Semáforo dañado",
  "Otro",
];

function claseEstado(estado) {
  const clave = (estado || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/\s+/g, "-");
  return "estado estado-" + clave;
}

function fecha(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
}

/* Tiempo relativo en corto: en una lista, «hace 2 h» se lee de un
   vistazo y la fecha completa no. La fecha exacta sigue en el
   historial del reporte, que es donde importa el dato preciso. */
function hace(iso) {
  if (!iso) return "";
  const segundos = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (segundos < 60) return "hace un momento";
  const minutos = Math.floor(segundos / 60);
  if (minutos < 60) return "hace " + minutos + " min";
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return "hace " + horas + " h";
  const dias = Math.floor(horas / 24);
  if (dias === 1) return "ayer";
  if (dias < 30) return "hace " + dias + " días";
  const meses = Math.floor(dias / 30);
  if (meses < 12) return "hace " + meses + (meses === 1 ? " mes" : " meses");
  return new Date(iso).toLocaleDateString("es-MX", { year: "numeric", month: "short" });
}
