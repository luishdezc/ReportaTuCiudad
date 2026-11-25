# Licencias de terceros usadas en el frontend

## Lucide (iconos)

Los trazos de los 49 iconos del sprite `js/iconos.js` vienen de
[Lucide](https://lucide.dev) y están copiados al repositorio a propósito: la
aplicación no debe depender de que haya internet para dibujar su interfaz.

```
ISC License

Copyright (c) for portions of Lucide are held by Cole Bemis 2013-2023 as part
of Feather (MIT). All other copyright (c) for Lucide are held by Lucide
Contributors 2025.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
```

## Las que sí se cargan desde la red

Estas tres se piden a un CDN y no están en el repositorio. Si falla la red se
degradan solas, sin romper la aplicación:

| Qué | De dónde | Si no carga |
|---|---|---|
| Vue 3.4.38 (compilación global) | unpkg | La aplicación no arranca |
| Leaflet 1.9.4 | unpkg | El mapa no se dibuja; el resto funciona |
| Mosaicos de mapa | OpenStreetMap | El mapa sale gris; los pines y la lista siguen |
| Tipografías Archivo y Roboto Mono | Google Fonts | Cae a Helvetica y a la monoespaciada del sistema |

Vue y Leaflet son las únicas dependencias de las que la aplicación no puede
prescindir, y están fijadas a una versión exacta para que una actualización del
CDN no cambie el comportamiento a media presentación.