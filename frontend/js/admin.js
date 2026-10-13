/* Panel de la cuenta municipal simulada */

const ESTADOS = ["Reportado", "En revisión", "Asignado", "En proceso", "Resuelto"];
let reporteSeleccionado = null;

document.addEventListener("DOMContentLoaded", () => {
  ESTADOS.forEach((e) => {
    document.getElementById("filtro-estado").appendChild(new Option(e, e));
    document.getElementById("nuevo-estado").appendChild(new Option(e, e));
  });

  document.getElementById("btn-login").onclick = entrar;
  document.getElementById("btn-recargar").onclick = cargarBandeja;
  document.getElementById("btn-actualizar").onclick = publicarActualizacion;
  document.getElementById("salir").onclick = (e) => { e.preventDefault(); API.cerrarSesion(); location.reload(); };

  const usuario = API.usuario();
  if (usuario && usuario.rol === "municipio") mostrarPanel();
});

async function entrar() {
  try {
    const datos = await API.post("/auth/login", {
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-password").value,
    });
    if (datos.usuario.rol !== "municipio") {
      throw new Error("Esta cuenta no tiene permisos de la cuenta municipal");
    }
    API.guardarSesion(datos.token, datos.usuario);
    mostrarPanel();
  } catch (e) {
    mostrarAviso("aviso-login", e.message, "error");
  }
}

function mostrarPanel() {
  document.getElementById("tarjeta-login").classList.add("oculto");
  document.getElementById("panel").classList.remove("oculto");
  cargarBandeja();
}

async function cargarBandeja() {
  const estado = document.getElementById("filtro-estado").value;
  try {
    const datos = await API.get("/admin/reportes" + (estado ? "?estado=" + encodeURIComponent(estado) : ""));

    document.getElementById("resumen").innerHTML = ESTADOS.map((e) =>
      `<div>${e}<strong>${datos.resumen[e] || 0}</strong></div>`).join("");

    document.getElementById("tabla-reportes").innerHTML = datos.reportes.map((r) => `
      <tr>
        <td><strong>${escapar(r.titulo)}</strong><br><span class="paso">${escapar(r.direccion || "")} · ${fecha(r.creadoEn)}</span></td>
        <td>${escapar(r.categoria)}</td>
        <td>${r.confirmaciones}</td>
        <td><span class="${claseEstado(r.estado)}">${r.estado}</span></td>
        <td><button class="pequeno secundario" onclick="atender('${r.reportId}')">Atender</button></td>
      </tr>`).join("") || "<tr><td colspan='5' class='paso'>No hay reportes con ese filtro.</td></tr>";
  } catch (e) {
    mostrarAviso("aviso-login", e.message, "error");
  }
}

async function atender(reportId) {
  const datos = await API.get("/reportes/" + reportId);
  reporteSeleccionado = datos.reporte;

  document.getElementById("tarjeta-atencion").classList.remove("oculto");
  document.getElementById("titulo-atencion").textContent = "Atender: " + datos.reporte.titulo;
  document.getElementById("nuevo-estado").value = datos.reporte.estado;
  document.getElementById("detalle-admin").innerHTML = `
    <p class="paso">Folio ${datos.reporte.reportId} · ${escapar(datos.reporte.categoria)} ·
      ${datos.reporte.confirmaciones} confirmaciones · reportado por ${escapar(datos.reporte.autorNombre)}</p>
    <p>${escapar(datos.reporte.descripcion)}</p>
    ${datos.reporte.foto ? `<img src="${datos.reporte.foto}" style="max-width:320px;border-radius:8px">` : ""}
    <div>${datos.historial.map((h) => `<div class="paso">${fecha(h.creadoEn)} · <strong>${h.estado}</strong> — ${escapar(h.mensaje)}</div>`).join("")}</div>`;
  document.getElementById("tarjeta-atencion").scrollIntoView({ behavior: "smooth" });
}

async function publicarActualizacion() {
  if (!reporteSeleccionado) return;
  const boton = document.getElementById("btn-actualizar");
  try {
    boton.disabled = true;
    boton.textContent = "Publicando...";
    const estado = document.getElementById("nuevo-estado").value;
    const archivo = document.getElementById("evidencia").files[0];

    if (estado === "Resuelto" && !archivo) {
      throw new Error("Para cerrar el reporte debes adjuntar la evidencia de la solución");
    }
    const evidenciaKey = await API.subirImagen(archivo, "/admin/evidencias");

    await API.patch("/admin/reportes/" + reporteSeleccionado.reportId + "/estado", {
      estado: estado,
      respuesta: document.getElementById("respuesta").value,
      evidenciaKey: evidenciaKey,
    });

    mostrarAviso("aviso-admin", "Actualización publicada. Se notificó al ciudadano y a quienes confirmaron el reporte.", "ok");
    document.getElementById("respuesta").value = "";
    document.getElementById("evidencia").value = "";
    cargarBandeja();
  } catch (e) {
    mostrarAviso("aviso-admin", e.message, "error");
  } finally {
    boton.disabled = false;
    boton.textContent = "Publicar actualización";
  }
}

function escapar(texto) {
  const div = document.createElement("div");
  div.textContent = texto == null ? "" : texto;
  return div.innerHTML;
}
