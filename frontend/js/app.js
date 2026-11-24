/* Vista del ciudadano: mapa, alta de reportes, confirmaciones y comentarios.
   Vue 3 en su compilación global (sin paso de construcción: el sitio se sirve
   como archivos estáticos desde S3). */

const { createApp } = Vue;

createApp({
  data() {
    return {
      estados: ESTADOS,
      categorias: CATEGORIAS,

      usuario: API.usuario(),
      reportes: [],
      cargando: true,
      errorCarga: "",

      filtroEstado: "",
      filtroCategoria: "",
      seleccionado: null,

      detalle: null,
      comentario: "",
      avisoDetalle: null,

      pestana: "mapa",
      actividad: [],
      estadisticas: null,
      avisos: [],
      sinLeer: 0,
      avisosAbierto: false,
      perfil: null,

      marcando: false,
      formAbierto: false,
      enviando: false,
      avisoForma: null,
      forma: this.formaVacia(),

      sesionAbierta: false,
      modoRegistro: false,
      credenciales: { nombre: "", colonia: "", email: "", password: "" },
      avisoSesion: null,
    };
  },

  computed: {
    textoConteo() {
      if (this.cargando) return "";
      const n = this.reportes.length;
      return n === 1 ? "1 reporte" : n + " reportes";
    },

    indiceEstado() {
      return this.detalle ? ESTADOS.indexOf(this.detalle.reporte.estado) : -1;
    },

    yaConfirme() {
      return !!(this.usuario && this.detalle &&
        this.detalle.confirmadores.includes(this.usuario.userId));
    },

    puedeConfirmar() {
      if (!this.usuario || !this.detalle) return false;
      return this.detalle.reporte.autorId !== this.usuario.userId && !this.yaConfirme;
    },

    sigoEsto() {
      return !!(this.usuario && this.detalle &&
        this.detalle.seguidores.includes(this.usuario.userId));
    },

    categoriasOrdenadas() {
      if (!this.estadisticas) return [];
      const entradas = Object.entries(this.estadisticas.porCategoria || {});
      if (!entradas.length) return [];
      const mayor = Math.max(...entradas.map((e) => e[1]));
      return entradas
        .sort((a, b) => b[1] - a[1])
        .map(([nombre, total]) => ({
          nombre,
          total,
          ancho: Math.round((total / mayor) * 100),
        }));
    },
  },

  watch: {
    /* Mientras el muro o el tablero ocupan el ancho completo, el mapa
       queda oculto y Leaflet pierde la medida del contenedor. Al
       volver hay que decirle que la recalcule o se dibuja cortado. */
    pestana(nueva) {
      if (nueva !== "mapa" || !this.mapa) return;
      this.$nextTick(() => this.mapa.invalidateSize());
    },
  },

  mounted() {
    this.iniciarMapa();
    this.cargarReportes();
    if (this.usuario) this.cargarAvisos();
  },

  methods: {
    claseEstado,
    fecha,
    hace,
    iconoCategoria,
    iconoEstado,

    /* Porcentaje acotado a 100, para las barras de avance. */
    porcentaje(parte, total) {
      if (!total) return 0;
      return Math.min(100, Math.round((parte / total) * 100));
    },

    /* Icono del movimiento en el muro de la ciudad. */
    iconoEvento(evento) {
      const iconos = {
        "reporte.creado": "megafono",
        "reporte.confirmado": "pulgar",
        "reporte.reabierto": "pulgar-abajo",
      };
      if (iconos[evento.tipo]) return iconos[evento.tipo];
      return iconoEstado(evento.estado);
    },

    /* Icono de cada insignia del perfil. */
    iconoInsignia(clave) {
      return {
        primer_reporte: "bandera",
        vigilante: "ojo",
        cronista: "megafono",
        respaldo: "pulgar",
        conversador: "comentario",
        resolutivo: "listo",
      }[clave] || "insignia";
    },

    formaVacia() {
      return {
        titulo: "", categoria: CATEGORIAS[0], direccion: "", descripcion: "",
        archivo: null, lat: null, lng: null,
      };
    },

    // ------------------------------------------------------------- mapa
    iniciarMapa() {
      this.mapa = L.map("mapa", { zoomControl: true }).setView([20.6597, -103.3496], 13);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap",
      }).addTo(this.mapa);
      this.capa = L.layerGroup().addTo(this.mapa);

      this.mapa.on("click", (evento) => {
        if (!this.marcando) return;
        this.forma.lat = evento.latlng.lat;
        this.forma.lng = evento.latlng.lng;
        if (this.marcadorNuevo) this.mapa.removeLayer(this.marcadorNuevo);
        this.marcadorNuevo = L.marker(evento.latlng, {
          icon: L.divIcon({
            className: "marcador-rtc",
            html: '<span class="pin pin-reportado">' +
                  '<svg class="ico"><use href="#i-mas"></use></svg></span>',
            iconSize: [32, 32],
            iconAnchor: [16, 30],
          }),
        }).addTo(this.mapa);
        this.marcando = false;
        this.formAbierto = true;
      });

      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (pos) => this.mapa.setView([pos.coords.latitude, pos.coords.longitude], 15),
          () => {}
        );
      }
    },

    /* El pin por omisión de Leaflet es una gota azul igual para todo.
       El nuestro lleva el icono de la categoría y el color del estado,
       así el mapa se lee sin abrir un solo reporte. */
    pinDe(reporte) {
      return L.divIcon({
        className: "marcador-rtc",
        html: '<span class="pin ' + claseEstado(reporte.estado).split(" ")[1].replace("estado-", "pin-") + '">' +
              '<svg class="ico"><use href="#i-' + iconoCategoria(reporte.categoria) + '"></use></svg>' +
              "</span>",
        iconSize: [32, 32],
        iconAnchor: [16, 30],
        popupAnchor: [0, -28],
      });
    },

    pintarMarcadores() {
      this.capa.clearLayers();
      this.reportes.forEach((r) => {
        const marcador = L.marker([r.lat, r.lng], { icon: this.pinDe(r) }).addTo(this.capa);
        marcador.bindPopup(
          "<h4>" + this.escapar(r.titulo) + "</h4>" +
          "<p style='margin:0'>" + this.escapar(r.categoria) + " — " + this.escapar(r.estado) + "</p>" +
          "<p style='margin:.2rem 0 0'>" + r.confirmaciones + " confirman</p>"
        );
        marcador.on("click", () => this.verDetalle(r.reportId));
      });
    },

    escapar(texto) {
      const div = document.createElement("div");
      div.textContent = texto == null ? "" : texto;
      return div.innerHTML;
    },

    // --------------------------------------------------------- reportes
    async cargarReportes() {
      this.cargando = true;
      this.errorCarga = "";
      const parametros = new URLSearchParams();
      if (this.filtroEstado) parametros.set("estado", this.filtroEstado);
      if (this.filtroCategoria) parametros.set("categoria", this.filtroCategoria);

      try {
        const datos = await API.get("/reportes?" + parametros.toString());
        this.reportes = datos.reportes;
        this.pintarMarcadores();
      } catch (e) {
        this.errorCarga = e.message;
      } finally {
        this.cargando = false;
      }
    },

    iniciarReporte() {
      if (!this.usuario) {
        this.abrirSesion();
        return;
      }
      if (this.forma.lat) {
        this.formAbierto = true;
      } else {
        this.marcando = true;
      }
    },

    async crearReporte() {
      this.avisoForma = null;
      if (!this.forma.lat) {
        this.avisoForma = { tipo: "error", texto: "Falta marcar la ubicación en el mapa." };
        return;
      }
      this.enviando = true;
      try {
        const fotoKey = await API.subirImagen(this.forma.archivo, "/reportes/carga");
        const datos = await API.post("/reportes", {
          titulo: this.forma.titulo,
          categoria: this.forma.categoria,
          descripcion: this.forma.descripcion,
          direccion: this.forma.direccion,
          lat: this.forma.lat,
          lng: this.forma.lng,
          fotoKey,
        });

        this.formAbierto = false;
        if (this.marcadorNuevo) this.mapa.removeLayer(this.marcadorNuevo);
        this.forma = this.formaVacia();
        await this.cargarReportes();
        await this.verDetalle(datos.reporte.reportId);
        this.avisoDetalle = {
          tipo: "ok",
          texto: "Reporte recibido. Te avisaremos por correo cada vez que cambie de estado.",
        };
      } catch (e) {
        this.avisoForma = { tipo: "error", texto: e.message };
      } finally {
        this.enviando = false;
      }
    },

    // ---------------------------------------------------------- detalle
    async verDetalle(reportId) {
      this.perfil = null;
      this.seleccionado = reportId;
      this.avisoDetalle = null;
      this.comentario = "";
      try {
        this.detalle = await API.get("/reportes/" + reportId);
      } catch (e) {
        this.avisoDetalle = { tipo: "error", texto: e.message };
      }
    },

    // ------------------------------------------- comunidad y estadísticas
    async verActividad() {
      this.pestana = "actividad";
      try {
        const datos = await API.get("/actividad?limite=40");
        this.actividad = datos.eventos;
      } catch (e) {
        this.errorCarga = e.message;
      }
    },

    async verEstadisticas() {
      this.pestana = "ciudad";
      try {
        this.estadisticas = await API.get("/estadisticas");
      } catch (e) {
        this.errorCarga = e.message;
      }
    },

    verboEvento(evento) {
      const verbos = {
        "reporte.creado": "Alguien levantó un reporte",
        "reporte.confirmado": evento.actor + " confirmó un reporte",
        "reporte.estado": "El municipio lo movió a " + evento.estado,
        "reporte.reabierto": "La comunidad lo reabrió",
      };
      return verbos[evento.tipo] || "Movimiento en un reporte";
    },

    claseEvento(evento) {
      if (evento.tipo === "reporte.creado") return "creado";
      if (evento.tipo === "reporte.confirmado") return "confirmado";
      if (evento.tipo === "reporte.reabierto") return "reabierto";
      return evento.estado === "Resuelto" ? "resuelto" : "estado";
    },

    // ------------------------------------------------------------ perfil
    async verPerfil(userId) {
      if (!userId) return;
      try {
        this.perfil = await API.get("/usuarios/" + userId + "/perfil");
        this.avisosAbierto = false;
      } catch (e) {
        this.avisoDetalle = { tipo: "error", texto: e.message };
      }
    },

    // ------------------------------------------------------------ avisos
    async cargarAvisos() {
      try {
        const datos = await API.get("/notificaciones");
        this.avisos = datos.notificaciones;
        this.sinLeer = datos.sinLeer;
      } catch (e) {
        // Los avisos no deben tumbar la vista principal si fallan.
        this.avisos = [];
      }
    },

    abrirAvisos() {
      this.avisosAbierto = true;
      this.cargarAvisos();
    },

    async marcarLeidos() {
      try {
        await API.post("/notificaciones/leidas", {});
        await this.cargarAvisos();
      } catch (e) {
        this.avisoDetalle = { tipo: "error", texto: e.message };
      }
    },

    irA(aviso) {
      this.avisosAbierto = false;
      if (aviso.reportId) this.verDetalle(aviso.reportId);
    },

    // ---------------------------------------------------- seguir reportes
    async alternarSeguir() {
      const ruta = "/reportes/" + this.detalle.reporte.reportId + "/seguidores";
      try {
        await API.peticion(this.sigoEsto ? "DELETE" : "POST", ruta, {});
        await this.verDetalle(this.detalle.reporte.reportId);
      } catch (e) {
        this.avisoDetalle = { tipo: "error", texto: e.message };
      }
    },

    async confirmar() {
      try {
        await API.post("/reportes/" + this.detalle.reporte.reportId + "/confirmaciones", {});
        await this.cargarReportes();
        await this.verDetalle(this.detalle.reporte.reportId);
      } catch (e) {
        this.avisoDetalle = { tipo: "error", texto: e.message };
      }
    },

    async comentar() {
      const texto = this.comentario.trim();
      if (!texto) return;
      try {
        await API.post("/reportes/" + this.detalle.reporte.reportId + "/comentarios", { texto });
        await this.verDetalle(this.detalle.reporte.reportId);
      } catch (e) {
        this.avisoDetalle = { tipo: "error", texto: e.message };
      }
    },

    async validar(resuelto) {
      try {
        const datos = await API.post(
          "/reportes/" + this.detalle.reporte.reportId + "/validacion", { resuelto });
        await this.cargarReportes();
        await this.verDetalle(this.seleccionado);
        this.avisoDetalle = {
          tipo: "ok",
          texto: datos.reabierto
            ? "Gracias. El reporte volvió a revisión porque varios dicen que el problema sigue."
            : "Gracias por confirmarlo.",
        };
      } catch (e) {
        this.avisoDetalle = { tipo: "error", texto: e.message };
      }
    },

    // ----------------------------------------------------------- sesión
    abrirSesion() {
      this.avisoSesion = null;
      this.sesionAbierta = true;
    },

    async entrar() {
      this.enviando = true;
      this.avisoSesion = null;
      try {
        const ruta = this.modoRegistro ? "/auth/registro" : "/auth/login";
        const datos = await API.post(ruta, this.credenciales);
        API.guardarSesion(datos.token, datos.usuario);
        this.usuario = datos.usuario;
        this.sesionAbierta = false;
        this.credenciales = { nombre: "", colonia: "", email: "", password: "" };
        this.cargarAvisos();
      } catch (e) {
        this.avisoSesion = { tipo: "error", texto: e.message };
      } finally {
        this.enviando = false;
      }
    },

    salir() {
      API.cerrarSesion();
      this.usuario = null;
      this.detalle = null;
      this.perfil = null;
      this.avisos = [];
      this.sinLeer = 0;
    },
  },
}).mount("#app");
