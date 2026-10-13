/* Cliente del API de ReportaTuCiudad + manejo de la sesion en el navegador */
const API = {
  base() {
    return (window.CONFIG && window.CONFIG.API_URL || "").replace(/\/$/, "");
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

    const respuesta = await fetch(this.base() + ruta, {
      method: metodo,
      headers: cabeceras,
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
    });

    const texto = await respuesta.text();
    const datos = texto ? JSON.parse(texto) : {};
    if (!respuesta.ok) throw new Error(datos.error || "Error " + respuesta.status);
    return datos;
  },

  get(ruta) { return this.peticion("GET", ruta); },
  post(ruta, cuerpo) { return this.peticion("POST", ruta, cuerpo); },
  patch(ruta, cuerpo) { return this.peticion("PATCH", ruta, cuerpo); },

  /* Sube la imagen directo a S3 con una URL prefirmada y devuelve la key */
  async subirImagen(archivo, ruta) {
    if (!archivo) return "";
    const permiso = await this.post(ruta, { contentType: archivo.type });
    const carga = await fetch(permiso.url, {
      method: "PUT",
      headers: { "Content-Type": archivo.type },
      body: archivo,
    });
    if (!carga.ok) throw new Error("No se pudo subir la imagen a S3");
    return permiso.key;
  },
};

function mostrarAviso(id, mensaje, tipo) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = mensaje;
  el.className = "aviso " + (tipo || "ok");
  el.classList.remove("oculto");
  if (tipo === "ok") setTimeout(() => el.classList.add("oculto"), 6000);
}

function fecha(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
}

function claseEstado(estado) {
  const clave = (estado || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, "-");
  return "estado estado-" + clave;
}
