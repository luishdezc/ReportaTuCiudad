/* Panel de la cuenta municipal simulada: bandeja por prioridad y cambio de estados. */

const { createApp } = Vue;

createApp({
  data() {
    const usuario = API.usuario();
    return {
      estados: ESTADOS,

      sesionActiva: !!(usuario && usuario.rol === "municipio"),
      credenciales: { email: "", password: "" },
      enviando: false,
      avisoAcceso: null,

      reportes: [],
      resumen: {},
      total: 0,
      filtroEstado: "",
      cargando: false,
      avisoBandeja: null,

      detalle: null,
      nuevoEstado: ESTADOS[0],
      respuesta: "",
      archivoEvidencia: null,
      publicando: false,
      avisoAtencion: null,
    };
  },

  computed: {
    indiceEstado() {
      return this.detalle ? ESTADOS.indexOf(this.detalle.reporte.estado) : -1;
    },
  },

  mounted() {
    if (this.sesionActiva) this.cargarBandeja();
  },

  methods: {
    claseEstado,
    fecha,
    hace,
    iconoCategoria,
    iconoEstado,

    // ----------------------------------------------------------- acceso
    async entrar() {
      this.enviando = true;
      this.avisoAcceso = null;
      try {
        const datos = await API.post("/auth/login", this.credenciales);
        if (datos.usuario.rol !== "municipio") {
          throw new Error("Esa cuenta es de ciudadano. Entra con la cuenta municipal.");
        }
        API.guardarSesion(datos.token, datos.usuario);
        this.sesionActiva = true;
        this.credenciales = { email: "", password: "" };
        this.cargarBandeja();
      } catch (e) {
        this.avisoAcceso = { tipo: "error", texto: e.message };
      } finally {
        this.enviando = false;
      }
    },

    salir() {
      API.cerrarSesion();
      this.sesionActiva = false;
      this.detalle = null;
      this.reportes = [];
    },

    // ---------------------------------------------------------- bandeja
    filtrar(estado) {
      this.filtroEstado = estado;
      this.cargarBandeja();
    },

    async cargarBandeja() {
      this.cargando = true;
      this.avisoBandeja = null;
      const consulta = this.filtroEstado
        ? "?estado=" + encodeURIComponent(this.filtroEstado)
        : "";
      try {
        const datos = await API.get("/admin/reportes" + consulta);
        this.reportes = datos.reportes;
        this.resumen = datos.resumen;
        // El total no cambia con el filtro: sale de la suma del resumen.
        this.total = Object.values(datos.resumen).reduce((a, b) => a + b, 0);
      } catch (e) {
        this.avisoBandeja = { tipo: "error", texto: e.message };
      } finally {
        this.cargando = false;
      }
    },

    // --------------------------------------------------------- atención
    async atender(reportId) {
      this.avisoAtencion = null;
      this.respuesta = "";
      this.archivoEvidencia = null;
      try {
        this.detalle = await API.get("/reportes/" + reportId);
        this.nuevoEstado = this.detalle.reporte.estado;
      } catch (e) {
        this.avisoBandeja = { tipo: "error", texto: e.message };
      }
    },

    cerrarAtencion() {
      this.detalle = null;
    },

    async publicar() {
      this.avisoAtencion = null;
      if (this.nuevoEstado === "Resuelto" && !this.archivoEvidencia
          && !this.detalle.reporte.evidencia) {
        this.avisoAtencion = {
          tipo: "error",
          texto: "Para cerrar el reporte falta adjuntar la evidencia de la solución.",
        };
        return;
      }

      this.publicando = true;
      try {
        const evidenciaKey = await API.subirImagen(this.archivoEvidencia, "/admin/evidencias");
        await API.patch("/admin/reportes/" + this.detalle.reporte.reportId + "/estado", {
          estado: this.nuevoEstado,
          respuesta: this.respuesta,
          evidenciaKey,
        });

        this.avisoAtencion = {
          tipo: "ok",
          texto: "Actualización publicada. Se notificó a quien reportó y a quienes lo confirmaron.",
        };
        this.respuesta = "";
        this.archivoEvidencia = null;
        await this.cargarBandeja();
        this.detalle = await API.get("/reportes/" + this.detalle.reporte.reportId);
      } catch (e) {
        this.avisoAtencion = { tipo: "error", texto: e.message };
      } finally {
        this.publicando = false;
      }
    },
  },
}).mount("#app");
