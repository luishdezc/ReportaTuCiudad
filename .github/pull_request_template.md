## Qué hace

<!-- Una o dos frases: qué cambia y por qué. -->

## Cómo probarlo

<!-- Pasos concretos. Ejemplo:
1. `cd backend && pytest`
2. `./scripts/deploy.sh lab`
3. Abrir el mapa y crear un reporte.
-->

## Tipo de cambio

- [ ] `feat` — funcionalidad nueva
- [ ] `fix` — corrección de un error
- [ ] `infra` — Terraform o scripts de despliegue
- [ ] `docs` — documentación
- [ ] `test` — pruebas

## Antes de pedir revisión

- [ ] `cd backend && pytest` pasa
- [ ] `ruff check backend/` pasa
- [ ] `terraform fmt -recursive` y `terraform validate` pasan
- [ ] No se versionó `terraform.tfstate`, `.env` ni credenciales
- [ ] La documentación afectada quedó actualizada

## Flujo que demuestra

<!-- Si aplica, cuál de los tres flujos end to end toca este cambio. -->
