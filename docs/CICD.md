# Integración y despliegue continuos

Dos pipelines en GitHub Actions, en `.github/workflows/`.

| Pipeline | Cuándo corre | Qué hace | Toca AWS |
|---|---|---|---|
| `ci.yml` | En cada Pull Request a `main` y en cada push a `main` | Linter, pruebas unitarias con cobertura, validación de Terraform, sintaxis del frontend y de los scripts, y revisión de que no se suban credenciales | No |
| `deploy.yml` | Automático al integrar en `main`, y manual desde **Actions** | Repite linter y pruebas, aplica Terraform, publica el frontend y corre la prueba de humo | Sí |

## CI: qué revisa cada trabajo

- **backend** — `ruff check` y `pytest` con cobertura. Falla si la cobertura baja de 85 %. Publica el número de pruebas en el resumen del workflow y guarda `coverage.xml` como artefacto.
- **infraestructura** — `terraform fmt -check`, `init -backend=false` y `validate`, tanto en `infra/` como en `infra/bootstrap/`. Sin credenciales: valida sintaxis y referencias entre recursos, no el estado real.
- **frontend** — `node --check` sobre cada archivo JavaScript y una comprobación de que `js/config.js` no está versionado (lo genera Terraform con la URL del API).
- **scripts** — `bash -n` y `shellcheck` sobre los scripts de despliegue.
- **secretos** — busca `*.tfstate`, `.env`, llaves `.pem` y patrones de llave de acceso de AWS (`AKIA…`) en los archivos versionados.

Los cinco trabajos corren en paralelo. Si alguno falla, el Pull Request queda marcado y no debe fusionarse.

> Si el CI falla en el paso de formato, corre `terraform fmt -recursive` en tu máquina y vuelve a subir los cambios. El pipeline imprime el diff para que veas qué cambiaría.

## Despliegue: cómo ejecutarlo

El despliegue se dispara solo con cada `push` a `main`, y antes de tocar la nube repite el linter y las pruebas: un merge no despliega nada que no haya pasado el mismo filtro que el Pull Request.

Hay una condición del laboratorio que conviene tener presente: las credenciales del AWS Academy Learner Lab caducan al cerrar la sesión. Si caducaron cuando corre el pipeline, falla en el primer paso con un mensaje que lo explica en lugar de un error de AWS sin contexto; basta actualizar los secretos y volver a lanzarlo desde **Actions**.

Antes de que corra, carga las credenciales de la sesión activa en **Settings → Secrets and variables → Actions**:

| Secreto | De dónde sale |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS Details → AWS CLI, en el Learner Lab |
| `AWS_SECRET_ACCESS_KEY` | igual |
| `AWS_SESSION_TOKEN` | igual (el Learner Lab siempre da credenciales temporales) |
| `MUNICIPIO_CORREO` | opcional: correo de la cuenta municipal, para la prueba de humo |
| `MUNICIPIO_CLAVE` | opcional: su contraseña |

Para lanzarlo a mano, en **Actions → Desplegar → Run workflow**, elige el ambiente (`lab` o `dev`) y la acción:

- **plan** — muestra qué cambiaría, sin tocar nada. Es lo que conviene correr primero.
- **apply** — crea los buckets si faltan, aplica Terraform, sube el frontend y corre la prueba de humo de los tres flujos.
- **destroy** — borra el ambiente.

El workflow comprueba primero que las credenciales sigan vigentes y, si caducaron, falla con un mensaje que lo dice en vez de dejar un error de AWS sin explicar.

Hay un `concurrency` por ambiente: dos despliegues simultáneos al mismo ambiente corromperían el estado de Terraform, así que el segundo espera.

## Pull Requests que demuestran la funcionalidad

Los tres cambios de la Fase 3 están pensados para entrar como Pull Requests separados, cada uno con su rama y su revisión. Así el historial muestra el proceso y no solo el resultado.

### PR 1 — `test/pruebas-unitarias`

**Qué incluye:** `backend/tests/` (59 pruebas), `backend/pytest.ini`, `backend/requirements-dev.txt`, `.ruff.toml`, y la corrección en `backend/src/` que las pruebas destaparon.

**Descripción sugerida:**

> Agrega la suite de pruebas unitarias del backend: 59 casos con pytest y moto, que simulan DynamoDB, S3, SQS, SNS y Secrets Manager. Cubren los tres flujos end to end, los permisos del panel municipal y los casos de error. Cobertura del 93 %.
>
> Las pruebas encontraron un error real: el historial de estados usaba la fecha con precisión de segundos como llave de orden, así que dos cambios dentro del mismo segundo se sobrescribían y el reporte perdía pasos de su historial. Se corrige con `ahora_preciso()`, que agrega microsegundos a la llave.

**Qué demuestra en la revisión:** el CI corre las 59 pruebas y publica la cobertura. Quien revisa puede ver el caso `test_recorrer_todos_los_estados`, que es el que falló antes de la corrección.

### PR 2 — `ci/pipelines`

**Qué incluye:** `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`, `.github/pull_request_template.md`, `docs/CICD.md`.

**Descripción sugerida:**

> Agrega los pipelines de integración y despliegue. El CI corre en cada Pull Request: linter, pruebas con umbral de cobertura, validación de Terraform, sintaxis del frontend y los scripts, y una revisión de que no se suban credenciales ni estado de Terraform. El despliegue queda manual porque las credenciales del Learner Lab caducan en cada sesión.

**Qué demuestra en la revisión:** este es el primer PR donde se ven los cinco checks en verde. Vale la pena abrirlo con una falla a propósito (por ejemplo, quitar un `assert`) para que quede registrado en el historial que el pipeline detiene los errores, y luego corregirla en el mismo PR.

### PR 3 — `feat/frontend-vue`

**Qué incluye:** `frontend/` completo y la sección del README sobre el frontend.

**Descripción sugerida:**

> Reescribe las dos interfaces con Vue 3 y un sistema visual propio. El mapa pasa a ser el elemento principal y los reportes se listan como fichas a un costado; el detalle abre en un panel lateral con el avance del reporte dibujado como una vía de cinco paradas. El panel municipal queda como una bandeja densa con el resumen por estado funcionando como filtro.
>
> No hay paso de compilación: Vue se carga desde CDN y el sitio se sigue publicando como archivos estáticos en S3, así que `infra/frontend.tf` no cambia.

**Qué demuestra en la revisión:** comparar capturas del antes y el después. El contrato del API no cambió, así que las pruebas del backend siguen pasando sin tocarse: eso es lo que hace revisable un cambio de frontend de este tamaño.

### Cómo trabajar cada PR

```bash
git checkout main
git pull origin main
git checkout -b test/pruebas-unitarias

# … cambios …

git add <archivos>
git commit -m "test(backend): suite de pruebas unitarias con pytest y moto"
git push -u origin test/pruebas-unitarias
```

Después, en GitHub: **Compare & pull request**, llenar la plantilla, esperar a que el CI pase en verde y pedir revisión a otro integrante. Quien revisa deja al menos un comentario antes de aprobar: un PR aprobado sin un solo comentario no demuestra revisión.

> Configura `main` como rama protegida en **Settings → Branches**: exige que el CI pase y que haya una aprobación antes de fusionar. Sin eso, el pipeline es decorativo.
