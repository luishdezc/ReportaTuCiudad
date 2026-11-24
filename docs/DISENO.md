# El diseño del frontend

Quién lo mantiene: integrante 1 (backend del flujo 1 y frontend).

## Por qué no hay un framework de CSS

Es la pregunta obvia, y la respuesta tiene que ver con dónde corre esto.

El sitio son archivos estáticos en S3, sin paso de construcción. Esa decisión
es la que mantiene barata la infraestructura: no hay servidor de Node, no hay
pipeline de empaquetado y `infra/frontend.tf` solo sube los archivos tal cual.
Meter Tailwind o Bootstrap tiene dos caminos, y los dos cuestan:

- **Por CDN.** Tailwind por CDN es un intérprete de 400 KB que reescribe los
  estilos en el navegador. Si la red del salón falla el día de la presentación,
  la aplicación aparece **sin un solo estilo**. Hoy, si falla la red, lo único
  que se pierde son los mosaicos del mapa.
- **Compilado y versionado.** Resuelve lo anterior, pero obliga a un paso de
  construcción en el pipeline y a versionar un CSS generado que nadie del
  equipo revisa en un Pull Request.

Y hay una tercera razón, menos técnica: lo que hacía que la interfaz se viera
sosa no era la falta de framework. Era que no había iconos, ni código de color,
ni jerarquía, y que el muro y el tablero vivían apretados en un rail de 384 px
mientras media pantalla se quedaba en gris. Un framework de utilidades no
arregla nada de eso por sí solo; de hecho su aspecto por omisión es justo lo
que se reconoce como «plantilla».

Lo que sí se tomó de fuera es el juego de iconos: **49 trazos de Lucide (ISC)**
copiados al repositorio como un sprite SVG en línea (`frontend/js/iconos.js`,
11 KB). Sin CDN, sin petición de red y heredando el color del texto.

## Las reglas del sistema

Todo vive en `frontend/styles.css` y arranca con variables en `:root`.

**La referencia es la señalética urbana.** Tinta azul oscura de placa de calle,
ámbar de obra en vía, verde de visto bueno. El folio es lo único en
monoespaciada, porque es un número de expediente y no decoración.

**Un color y un icono por categoría, y ese par viaja completo.** El bache es
terracota con la barrera de obra en el pin del mapa, en la ficha de la lista, en
la barra del tablero y en la fila del panel municipal. Quien usa la aplicación
aprende el código una vez y le sirve en todas partes.

| Categoría | Color | Icono |
|---|---|---|
| Bache | terracota | barrera de obra |
| Luminaria dañada | ámbar | foco apagado |
| Acumulación de basura | verde oliva | bote |
| Fuga de agua | azul | gotas |
| Árbol caído | verde | árbol |
| Semáforo dañado | rojo | señal |
| Otro | pizarra | interrogación |

**El estado es el color del pin.** Ámbar sin atender, azul en trámite, verde
resuelto. La leyenda está en la esquina del mapa, así que el mapa se lee sin
abrir un solo reporte.

**Un icono solo si aporta.** Nada decorativo: todos van con `aria-hidden` y el
texto al lado, o con `aria-label` cuando el botón es solo icono (la campana).

## Decisiones que vale la pena defender

**El mapa desaparece en Actividad y La ciudad.** Era el peor problema de la
versión anterior: el muro y el tablero se amontonaban en el rail mientras el
mapa ocupaba el 70 % de la pantalla sin aportar nada. Ahora esas dos pestañas
usan el ancho completo y el mapa solo existe en Reportes. Leaflet pierde la
medida del contenedor mientras está oculto, así que al volver hay un
`invalidateSize()`; sin eso el mapa se dibuja cortado.

**Pines propios en vez de la gota azul de Leaflet.** Un `divIcon` con el icono
de la categoría y el color del estado. Es el cambio que más información agrega
por línea de código.

**Esqueletos en vez de «Cargando…».** El hueco tiene la forma de lo que va a
llegar, así que la lista no salta cuando entran los datos.

**Tiempos relativos en las listas, fecha exacta en el historial.** «hace 2 h» se
lee de un vistazo; el dato preciso importa en el historial del reporte, que es
donde se audita qué hizo el municipio y cuándo.

**El select es nuestro.** Se le quita la flecha del sistema y se dibuja una en
SVG embebido, porque el control nativo se ve distinto en cada navegador y el
del profesor no tiene por qué ser el mismo que el nuestro.

**En el teléfono el mapa va primero.** Quien reporta está parado en la calle y
lo que necesita a la mano es marcar el punto. Abajo de 560 px los enlaces de la
barra se quedan en iconos, porque con la campana y el nombre de la cuenta la
navegación se partía en dos renglones.

## Cómo se revisa

`revisar.py` (en el material de trabajo, no en el repositorio) abre las ocho
pantallas en Chromium con Playwright —escritorio y teléfono—, captura cada una
y falla si aparece un error de consola, si queda una llave `{{ }}` sin
interpretar, si hay desbordamiento horizontal en móvil o si algún `<use>`
apunta a un símbolo que no existe en el sprite. Esa última revisión es la que
atrapa un icono mal escrito, que de otro modo se vería simplemente como un
hueco.

Los errores que encontró durante este rediseño: la etiqueta del enlace de
navegación partiendo la barra en dos renglones en el teléfono, el botón
flotante partido en dos líneas, la palomita dibujada en la parada *actual* de
la vía (que todavía no está hecha) y el icono `signal-zero` del semáforo, que a
19 px era prácticamente invisible.
