/* Vista del ciudadano: mapa, alta de reportes, confirmaciones y comentarios */

const ESTADOS = ["Reportado", "En revisión", "Asignado", "En proceso", "Resuelto"];
const CATEGORIAS = ["Bache", "Luminaria dañada", "Acumulación de basura", "Fuga de agua",
                    "Árbol caído", "Semáforo dañado", "Otro"];

let mapa, capaMarcadores, marcadorNuevo = null, coordenadas = null, reportesCargados = [];

document.addEventListener("DOMContentLoaded", () => {
  llenarSelect("rep-categoria", CATEGORIAS, false);
  llenarSelect("filtro-categoria", CATEGORIAS, true);
  llenarSelect("filtro-estado", ESTADOS, true);
  iniciarMapa();
  pintarSesion();
  cargarReportes();

  document.getElementById("btn-login").onclick = iniciarSesion;
  document.getElementById("btn-registro").onclick = registrarse;
  document.getElementById("btn-crear").onclick = crearReporte;
  document.getElementById("btn-filtrar").onclick = cargarReportes;
  document.getElementById("salir").onclick = (e) => { e.preventDefault(); API.cerrarSesion(); location.reload(); };
  document.getElementById("btn-ir-registro").onclick = () => alternarFormularios(true);
  document.getElementById("btn-ir-login").onclick = () => alternarFormularios(false);
});

function llenarSelect(id, valores, conTodos) {
  const select = document.getElementById(id);
  if (!select) return;
  if (conTodos && !select.options.length) select.innerHTML = "<option value=''>Todos</option>";
  valores.forEach((v) => {
    const opcion = document.createElement("option");
    opcion.value = v;
    opcion.textContent = v;
    select.appendChild(opcion);
  });
}

function alternarFormularios(mostrarRegistro) {
  document.getElementById("formulario-registro").classList.toggle("oculto", !mostrarRegistro);
  document.getElementById("formulario-login").classList.toggle("oculto", mostrarRegistro);
}

/* ------------------------------------------------------------------ mapa */
function iniciarMapa() {
  mapa = L.map("mapa").setView([20.6597, -103.3496], 13); // Guadalajara por defecto
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap",
  }).addTo(mapa);
  capaMarcadores = L.layerGroup().addTo(mapa);

  mapa.on("click", (evento) => {
    if (!API.token()) return;
    coordenadas = { lat: evento.latlng.lat, lng: evento.latlng.lng };
    document.getElementById("rep-coords").value =
      coordenadas.lat.toFixed(5) + ", " + coordenadas.lng.toFixed(5);
    if (marcadorNuevo) mapa.removeLayer(marcadorNuevo);
    marcadorNuevo = L.marker([coordenadas.lat, coordenadas.lng]).addTo(mapa)
      .bindPopup("Ubicación del nuevo reporte").openPopup();
  });

  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => mapa.setView([pos.coords.latitude, pos.coords.longitude], 15),
      () => {}
    );
  }
}

/* --------------------------------------------------------------- sesión */
function pintarSesion() {
  const usuario = API.usuario();
  document.getElementById("salir").classList.toggle("oculto", !usuario);
  document.getElementById("tarjeta-reporte").classList.toggle("oculto", !usuario);
  document.getElementById("tarjeta-sesion").classList.toggle("oculto", !!usuario);
}

async function iniciarSesion() {
  try {
    const datos = await API.post("/auth/login", {
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-password").value,
    });
    API.guardarSesion(datos.token, datos.usuario);
    pintarSesion();
    cargarReportes();
    mostrarAviso("aviso-sesion", "Bienvenido, " + datos.usuario.nombre, "ok");
  } catch (e) {
    mostrarAviso("aviso-sesion", e.message, "error");
  }
}

async function registrarse() {
  try {
    const datos = await API.post("/auth/registro", {
      nombre: document.getElementById("reg-nombre").value,
      email: document.getElementById("reg-email").value,
      colonia: document.getElementById("reg-colonia").value,
      password: document.getElementById("reg-password").value,
    });
    API.guardarSesion(datos.token, datos.usuario);
    pintarSesion();
    mostrarAviso("aviso-sesion", "Cuenta creada. Ya puedes reportar.", "ok");
  } catch (e) {
    mostrarAviso("aviso-sesion", e.message, "error");
  }
}

/* -------------------------------------------------------------- reportes */
async function crearReporte() {
  const boton = document.getElementById("btn-crear");
  try {
    if (!coordenadas) throw new Error("Marca la ubicación del problema en el mapa");
    boton.disabled = true;
    boton.textContent = "Enviando...";

    const archivo = document.getElementById("rep-foto").files[0];
    const fotoKey = await API.subirImagen(archivo, "/reportes/carga");

    const datos = await API.post("/reportes", {
      titulo: document.getElementById("rep-titulo").value,
      categoria: document.getElementById("rep-categoria").value,
      descripcion: document.getElementById("rep-descripcion").value,
      direccion: document.getElementById("rep-direccion").value,
      lat: coordenadas.lat,
      lng: coordenadas.lng,
      fotoKey: fotoKey,
    });

    mostrarAviso("aviso-reporte",
      "Reporte enviado con folio " + datos.reporte.reportId + ". Recibirás un correo con las actualizaciones.", "ok");
    ["rep-titulo", "rep-descripcion", "rep-direccion", "rep-coords"].forEach((id) => {
      document.getElementById(id).value = "";
    });
    document.getElementById("rep-foto").value = "";
    if (marcadorNuevo) mapa.removeLayer(marcadorNuevo);
    coordenadas = null;
    cargarReportes();
  } catch (e) {
    mostrarAviso("aviso-reporte", e.message, "error");
  } finally {
    boton.disabled = false;
    boton.textContent = "Enviar reporte";
  }
}

async function cargarReportes() {
  const parametros = new URLSearchParams();
  const estado = document.getElementById("filtro-estado").value;
  const categoria = document.getElementById("filtro-categoria").value;
  if (estado) parametros.set("estado", estado);
  if (categoria) parametros.set("categoria", categoria);

  try {
    const datos = await API.get("/reportes?" + parametros.toString());
    reportesCargados = datos.reportes;
    document.getElementById("titulo-lista").textContent =
      "Reportes de la zona (" + datos.total + ")";
    pintarMarcadores(datos.reportes);
    pintarLista(datos.reportes);
  } catch (e) {
    document.getElementById("lista-reportes").innerHTML =
      "<p class='aviso error'>" + e.message + "</p>";
  }
}

function pintarMarcadores(reportes) {
  capaMarcadores.clearLayers();
  reportes.forEach((r) => {
    const marcador = L.marker([r.lat, r.lng]).addTo(capaMarcadores);
    marcador.bindPopup(
      "<strong>" + r.titulo + "</strong><br>" + r.categoria +
      "<br><span class='" + claseEstado(r.estado) + "'>" + r.estado + "</span>" +
      "<br>" + r.confirmaciones + " confirmaciones"
    );
    marcador.on("click", () => verDetalle(r.reportId));
  });
}

function pintarLista(reportes) {
  const contenedor = document.getElementById("lista-reportes");
  if (!reportes.length) {
    contenedor.innerHTML = "<p class='paso'>Todavía no hay reportes con esos filtros.</p>";
    return;
  }
  contenedor.innerHTML = reportes.map((r) => `
    <div class="reporte">
      <h3>${escapar(r.titulo)}</h3>
      <div class="meta">
        <span class="${claseEstado(r.estado)}">${r.estado}</span>
        <span>${escapar(r.categoria)}</span>
        <span>${r.confirmaciones} confirmaciones</span>
        <span>${r.comentarios} comentarios</span>
        <span>${fecha(r.creadoEn)}</span>
      </div>
      <button class="pequeno secundario" onclick="verDetalle('${r.reportId}')">Ver detalle</button>
    </div>`).join("");
}

/* --------------------------------------------------------------- detalle */
async function verDetalle(reportId) {
  const tarjeta = document.getElementById("tarjeta-detalle");
  tarjeta.classList.remove("oculto");
  const caja = document.getElementById("detalle");
  caja.innerHTML = "<p class='paso'>Cargando...</p>";

  try {
    const datos = await API.get("/reportes/" + reportId);
    const r = datos.reporte;
    const usuario = API.usuario();
    const esAutor = usuario && usuario.userId === r.autorId;
    const yaConfirmo = usuario && datos.confirmadores.includes(usuario.userId);

    caja.innerHTML = `
      <h3>${escapar(r.titulo)} <span class="${claseEstado(r.estado)}">${r.estado}</span></h3>
      <p class="paso">Folio ${r.reportId} · ${escapar(r.categoria)} · ${escapar(r.direccion || "sin referencia")} · ${fecha(r.creadoEn)}</p>
      <p>${escapar(r.descripcion)}</p>
      ${r.foto ? `<img src="${r.foto}" alt="Fotografía del reporte">` : ""}
      ${r.respuestaMunicipal ? `<div class="comentario oficial"><strong>Cuenta municipal:</strong> ${escapar(r.respuestaMunicipal)}</div>` : ""}
      ${r.evidencia ? `<p class="paso">Evidencia de la solución:</p><img src="${r.evidencia}" alt="Evidencia">` : ""}

      <h3 style="margin-top:14px">Seguimiento</h3>
      ${datos.historial.map((h) => `<div class="paso">${fecha(h.creadoEn)} · <strong>${h.estado}</strong> — ${escapar(h.mensaje)}</div>`).join("")}

      <h3 style="margin-top:14px">Comentarios (${datos.comentarios.length})</h3>
      ${datos.comentarios.map((cm) => `
        <div class="comentario ${cm.oficial ? "oficial" : ""}">
          <strong>${escapar(cm.autor || "Ciudadano")}${cm.oficial ? " (municipio)" : ""}:</strong>
          ${escapar(cm.texto)}<br><span class="paso">${fecha(cm.creadoEn)}</span>
        </div>`).join("") || "<p class='paso'>Sé el primero en comentar.</p>"}

      ${usuario ? `
        <textarea id="nuevo-comentario" placeholder="Escribe un comentario"></textarea>
        <button class="pequeno" onclick="comentar('${r.reportId}')">Comentar</button>
        ${!esAutor && !yaConfirmo ? `<button class="pequeno secundario" onclick="confirmar('${r.reportId}')">Yo también lo vi (${r.confirmaciones})</button>` : ""}
        ${r.estado === "Resuelto" ? `
          <p class="paso" style="margin-top:12px">¿El problema realmente quedó solucionado?</p>
          <button class="pequeno" onclick="validar('${r.reportId}', true)">Sí, quedó resuelto</button>
          <button class="pequeno secundario" onclick="validar('${r.reportId}', false)">No, sigue igual</button>` : ""}
      ` : "<p class='paso'>Inicia sesión para confirmar o comentar.</p>"}
      <div id="aviso-detalle" class="aviso oculto"></div>`;

    tarjeta.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    caja.innerHTML = "<p class='aviso error'>" + e.message + "</p>";
  }
}

async function confirmar(reportId) {
  try {
    await API.post("/reportes/" + reportId + "/confirmaciones", {});
    await cargarReportes();
    verDetalle(reportId);
  } catch (e) {
    mostrarAviso("aviso-detalle", e.message, "error");
  }
}

async function comentar(reportId) {
  const texto = document.getElementById("nuevo-comentario").value.trim();
  if (!texto) return;
  try {
    await API.post("/reportes/" + reportId + "/comentarios", { texto });
    verDetalle(reportId);
  } catch (e) {
    mostrarAviso("aviso-detalle", e.message, "error");
  }
}

async function validar(reportId, resuelto) {
  try {
    const datos = await API.post("/reportes/" + reportId + "/validacion", { resuelto });
    mostrarAviso("aviso-detalle",
      datos.reabierto ? "Gracias. El reporte se reabrió para revisión." : "Gracias por confirmar.", "ok");
    await cargarReportes();
  } catch (e) {
    mostrarAviso("aviso-detalle", e.message, "error");
  }
}

function escapar(texto) {
  const div = document.createElement("div");
  div.textContent = texto == null ? "" : texto;
  return div.innerHTML;
}
