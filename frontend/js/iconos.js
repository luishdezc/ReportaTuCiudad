/* Sprite de iconos en linea.
   -------------------------------------------------------------------
   Los trazos son de Lucide (https://lucide.dev, licencia ISC) y estan
   copiados aqui a proposito: la red del salon puede fallar y los iconos
   tienen que seguir dibujandose. Se usan asi:

     <svg class="ico"><use href="#i-bache"></use></svg>

   El color lo heredan de `currentColor` y el tamano del CSS.          */

const SPRITE_ICONOS =
  '<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true" ' +
  'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
  'stroke-linejoin="round">' +
  '<symbol id="i-bache" viewBox="0 0 24 24"><rect x="2" y="6" width="20" height="8" rx="1" /> <path d="M17 14v7" ' +
  '/> <path d="M7 14v7" /> <path d="M17 3v3" /> <path d="M7 3v3" /> <path d="M10 14 2.3 6.3" /> <path d="m14 6 7.' +
  '7 7.7" /> <path d="m8 6 8 8" /></symbol><symbol id="i-luminaria" viewBox="0 0 24 24"><path d="M16.8 11.2c.8-.9' +
  ' 1.2-2 1.2-3.2a6 6 0 0 0-9.3-5" /> <path d="m2 2 20 20" /> <path d="M6.3 6.3a4.67 4.67 0 0 0 1.2 5.2c.7.7 1.3 ' +
  '1.5 1.5 2.5" /> <path d="M9 18h6" /> <path d="M10 22h4" /></symbol><symbol id="i-basura" viewBox="0 0 24 24"><' +
  'path d="M10 11v6" /> <path d="M14 11v6" /> <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" /> <path d="M3 6' +
  'h18" /> <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></symbol><symbol id="i-agua" viewBox="0 0 24 24"><p' +
  'ath d="M7 16.3c2.2 0 4-1.83 4-4.05 0-1.16-.57-2.26-1.71-3.19S7.29 6.75 7 5.3c-.29 1.45-1.14 2.84-2.29 3.76S3 1' +
  '1.1 3 12.25c0 2.22 1.8 4.05 4 4.05z" /> <path d="M12.56 6.6A10.97 10.97 0 0 0 14 3.02c.5 2.5 2 4.9 4 6.5s3 3.5' +
  ' 3 5.5a6.98 6.98 0 0 1-11.91 4.97" /></symbol><symbol id="i-arbol" viewBox="0 0 24 24"><path d="M8 19a4 4 0 0 ' +
  '1-2.24-7.32A3.5 3.5 0 0 1 9 6.03V6a3 3 0 1 1 6 0v.04a3.5 3.5 0 0 1 3.24 5.65A4 4 0 0 1 16 19Z" /> <path d="M12' +
  ' 19v3" /></symbol><symbol id="i-semaforo" viewBox="0 0 24 24"><path d="M2 20h.01" /> <path d="M7 20v-4" /> <pa' +
  'th d="M12 20v-8" /> <path d="M17 20V8" /> <path d="M22 4v16" /></symbol><symbol id="i-otro" viewBox="0 0 24 24' +
  '"><circle cx="12" cy="12" r="10" /> <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /> <path d="M12 17h.01" /><' +
  '/symbol><symbol id="i-mapa" viewBox="0 0 24 24"><path d="M18 8c0 3.613-3.869 7.429-5.393 8.795a1 1 0 0 1-1.214' +
  ' 0C9.87 15.429 6 11.613 6 8a6 6 0 0 1 12 0" /> <circle cx="12" cy="8" r="2" /> <path d="M8.714 14h-3.71a1 1 0 ' +
  '0 0-.948.683l-2.004 6A1 1 0 0 0 3 22h18a1 1 0 0 0 .948-1.316l-2-6a1 1 0 0 0-.949-.684h-3.712" /></symbol><symb' +
  'ol id="i-pin" viewBox="0 0 24 24"><path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20' +
  '.193 4 14.993 4 10a8 8 0 0 1 16 0" /> <circle cx="12" cy="10" r="3" /></symbol><symbol id="i-campana" viewBox=' +
  '"0 0 24 24"><path d="M10.268 21a2 2 0 0 0 3.464 0" /> <path d="M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1' +
  '.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326" /></symbol><symbol id="i-usuar' +
  'io" viewBox="0 0 24 24"><circle cx="12" cy="8" r="5" /> <path d="M20 21a8 8 0 0 0-16 0" /></symbol><symbol id=' +
  '"i-salir" viewBox="0 0 24 24"><path d="m16 17 5-5-5-5" /> <path d="M21 12H9" /> <path d="M9 21H5a2 2 0 0 1-2-2' +
  'V5a2 2 0 0 1 2-2h4" /></symbol><symbol id="i-entrar" viewBox="0 0 24 24"><path d="m10 17 5-5-5-5" /> <path d="' +
  'M15 12H3" /> <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" /></symbol><symbol id="i-municipio" viewBox="' +
  '0 0 24 24"><path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z" /> <path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2' +
  ' 2h2" /> <path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2" /> <path d="M10 6h4" /> <path d="M10 10h4" /> <pat' +
  'h d="M10 14h4" /> <path d="M10 18h4" /></symbol><symbol id="i-listo" viewBox="0 0 24 24"><path d="M21.801 10A1' +
  '0 10 0 1 1 17 3.335" /> <path d="m9 11 3 3L22 4" /></symbol><symbol id="i-reloj" viewBox="0 0 24 24"><path d="' +
  'M12 6v6l4 2" /> <circle cx="12" cy="12" r="10" /></symbol><symbol id="i-comentario" viewBox="0 0 24 24"><path ' +
  'd="M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 ' +
  '0 1 2 2z" /> <path d="M7 11h10" /> <path d="M7 15h6" /> <path d="M7 7h8" /></symbol><symbol id="i-vecinos" vie' +
  'wBox="0 0 24 24"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /> <path d="M16 3.128a4 4 0 0 1 0 7.744" ' +
  '/> <path d="M22 21v-2a4 4 0 0 0-3-3.87" /> <circle cx="9" cy="7" r="4" /></symbol><symbol id="i-mas" viewBox="' +
  '0 0 24 24"><path d="M5 12h14" /> <path d="M12 5v14" /></symbol><symbol id="i-cerrar" viewBox="0 0 24 24"><path' +
  ' d="M18 6 6 18" /> <path d="m6 6 12 12" /></symbol><symbol id="i-camara" viewBox="0 0 24 24"><path d="M13.997 ' +
  '4a2 2 0 0 1 1.76 1.05l.486.9A2 2 0 0 0 18.003 7H20a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2' +
  '-2h1.997a2 2 0 0 0 1.759-1.048l.489-.904A2 2 0 0 1 10.004 4z" /> <circle cx="12" cy="13" r="3" /></symbol><sym' +
  'bol id="i-flecha" viewBox="0 0 24 24"><path d="m9 18 6-6-6-6" /></symbol><symbol id="i-abajo" viewBox="0 0 24 ' +
  '24"><path d="m6 9 6 6 6-6" /></symbol><symbol id="i-filtro" viewBox="0 0 24 24"><path d="M2 5h20" /> <path d="' +
  'M6 12h12" /> <path d="M9 19h6" /></symbol><symbol id="i-insignia" viewBox="0 0 24 24"><path d="m15.477 12.89 1' +
  '.515 8.526a.5.5 0 0 1-.81.47l-3.58-2.687a1 1 0 0 0-1.197 0l-3.586 2.686a.5.5 0 0 1-.81-.469l1.514-8.526" /> <c' +
  'ircle cx="12" cy="8" r="6" /></symbol><symbol id="i-pulso" viewBox="0 0 24 24"><path d="M22 12h-2.48a2 2 0 0 0' +
  '-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2" /></symb' +
  'ol><symbol id="i-barras" viewBox="0 0 24 24"><path d="M3 3v16a2 2 0 0 0 2 2h16" /> <path d="M18 17V9" /> <path' +
  ' d="M13 17V5" /> <path d="M8 17v-3" /></symbol><symbol id="i-ojo" viewBox="0 0 24 24"><path d="M2.062 12.348a1' +
  ' 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0" /> <circle cx="12" cy=' +
  '"12" r="3" /></symbol><symbol id="i-escudo" viewBox="0 0 24 24"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 ' +
  '1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5' +
  'a1 1 0 0 1 1 1z" /> <path d="m9 12 2 2 4-4" /></symbol><symbol id="i-externo" viewBox="0 0 24 24"><path d="M7 ' +
  '7h10v10" /> <path d="M7 17 17 7" /></symbol><symbol id="i-imagen" viewBox="0 0 24 24"><rect width="18" height=' +
  '"18" x="3" y="3" rx="2" ry="2" /> <circle cx="9" cy="9" r="2" /> <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0' +
  'L6 21" /></symbol><symbol id="i-alerta" viewBox="0 0 24 24"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2' +
  ' 0 0 0 4 21h16a2 2 0 0 0 1.73-3" /> <path d="M12 9v4" /> <path d="M12 17h.01" /></symbol><symbol id="i-enviar"' +
  ' viewBox="0 0 24 24"><path d="M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5' +
  ' 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z" /> <path d="m21.854 2.147-10.94 10.939" /></symbol><symbol id' +
  '="i-tendencia" viewBox="0 0 24 24"><path d="M16 7h6v6" /> <path d="m22 7-8.5 8.5-5-5L2 17" /></symbol><symbol ' +
  'id="i-buscar" viewBox="0 0 24 24"><path d="m21 21-4.34-4.34" /> <circle cx="11" cy="11" r="8" /></symbol><symb' +
  'ol id="i-megafono" viewBox="0 0 24 24"><path d="M11 6a13 13 0 0 0 8.4-2.8A1 1 0 0 1 21 4v12a1 1 0 0 1-1.6.8A13' +
  ' 13 0 0 0 11 14H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z" /> <path d="M6 14a12 12 0 0 0 2.4 7.2 2 2 0 0 0 3.2-2.4A8 8 ' +
  '0 0 1 10 14" /> <path d="M8 6v8" /></symbol><symbol id="i-obra" viewBox="0 0 24 24"><path d="M10 10V5a1 1 0 0 ' +
  '1 1-1h2a1 1 0 0 1 1 1v5" /> <path d="M14 6a6 6 0 0 1 6 6v3" /> <path d="M4 15v-3a6 6 0 0 1 6-6" /> <rect x="2"' +
  ' y="15" width="20" height="4" rx="1" /></symbol><symbol id="i-chispa" viewBox="0 0 24 24"><path d="M11.017 2.8' +
  '14a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.' +
  '594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.5' +
  '58-1.051a2 2 0 0 0 1.594-1.594z" /> <path d="M20 2v4" /> <path d="M22 4h-4" /> <circle cx="4" cy="20" r="2" />' +
  '</symbol><symbol id="i-centrar" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /> <line x1="22" x2="18" y1' +
  '="12" y2="12" /> <line x1="6" x2="2" y1="12" y2="12" /> <line x1="12" x2="12" y1="6" y2="2" /> <line x1="12" x' +
  '2="12" y1="22" y2="18" /></symbol><symbol id="i-calendario" viewBox="0 0 24 24"><path d="M8 2v4" /> <path d="M' +
  '16 2v4" /> <rect width="18" height="18" x="3" y="4" rx="2" /> <path d="M3 10h18" /></symbol><symbol id="i-cand' +
  'ado" viewBox="0 0 24 24"><rect width="18" height="11" x="3" y="11" rx="2" ry="2" /> <path d="M7 11V7a5 5 0 0 1' +
  ' 10 0v4" /></symbol><symbol id="i-recargar" viewBox="0 0 24 24"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6' +
  '.74 2.74L21 8" /> <path d="M21 3v5h-5" /> <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" /> <pa' +
  'th d="M8 16H3v5" /></symbol><symbol id="i-info" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /> <path d=' +
  '"M12 16v-4" /> <path d="M12 8h.01" /></symbol><symbol id="i-pulgar" viewBox="0 0 24 24"><path d="M7 10v12" /> ' +
  '<path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.' +
  '76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" /></symbol><symbol id="i-pulgar-abajo" viewBox="0 0 24 24' +
  '"><path d="M17 14V2" /> <path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2' +
  ' 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z" /></symbol><symbol id="i-seguir" v' +
  'iewBox="0 0 24 24"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z" /></symbol><symbol id="i-sigu' +
  'iendo" viewBox="0 0 24 24"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2Z" /> <path d="m9 10 2 2 4-' +
  '4" /></symbol><symbol id="i-bandera" viewBox="0 0 24 24"><path d="M4 22V4a1 1 0 0 1 .4-.8A6 6 0 0 1 8 2c3 0 5 ' +
  '2 7.333 2q2 0 3.067-.8A1 1 0 0 1 20 4v10a1 1 0 0 1-.4.8A6 6 0 0 1 16 16c-3 0-5-2-8-2a6 6 0 0 0-4 1.528" /></sy' +
  'mbol><symbol id="i-medidor" viewBox="0 0 24 24"><path d="m12 14 4-4" /> <path d="M3.34 19a10 10 0 1 1 17.32 0"' +
  ' /></symbol>' +
  '</svg>';

/* Que icono le toca a cada categoria de reporte. */
const ICONO_CATEGORIA = {
  "Bache": "bache",
  "Luminaria da\u00f1ada": "luminaria",
  "Acumulaci\u00f3n de basura": "basura",
  "Fuga de agua": "agua",
  "\u00c1rbol ca\u00eddo": "arbol",
  "Sem\u00e1foro da\u00f1ado": "semaforo",
  "Otro": "otro",
};

function iconoCategoria(categoria) {
  return ICONO_CATEGORIA[categoria] || "otro";
}

/* Que icono le toca a cada estado del reporte. */
const ICONO_ESTADO = {
  "Reportado": "megafono",
  "En revisi\u00f3n": "ojo",
  "Asignado": "obra",
  "En proceso": "obra",
  "Resuelto": "listo",
};

function iconoEstado(estado) {
  return ICONO_ESTADO[estado] || "info";
}

/* El sprite se inyecta una sola vez, al abrir la pagina. */
document.addEventListener("DOMContentLoaded", function () {
  document.body.insertAdjacentHTML("afterbegin", SPRITE_ICONOS);
});
