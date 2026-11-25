# Cómo trabajamos en el repositorio

## Ramas

- `main`: siempre desplegable. No se hace push directo.
- `feat/<tema>`, `fix/<tema>`, `docs/<tema>`: ramas de trabajo.
- Todo entra por pull request con al menos una revisión de otro integrante.

## Mensajes de commit

Formato `tipo(alcance): descripción en presente`.

```
feat(reportes): alta de reportes con foto y ubicacion
fix(admin): validar evidencia obligatoria al cerrar
infra(lambda): empaquetar backend con archive_file
docs(api): documentar rutas de interacciones
```

Tipos: `feat`, `fix`, `infra`, `docs`, `test`, `chore`.

## Reparto del trabajo (para que haya commits de los tres integrantes)

| Integrante | Rol | Archivos que le tocan |
|---|---|---|
| Integrante 1 | Backend del flujo 1 y frontend | `backend/src/handler_reportes.py`, `backend/src/handler_social.py`, `frontend/**`, `docs/DISENO.md` |
| Integrante 2 | Backend del flujo 2 y CI/CD | `backend/src/handler_admin.py`, `backend/src/handler_auth.py`, `.github/**`, `scripts/deploy.sh`, `docs/CICD.md` |
| Integrante 3 | Backend del flujo 3 y monitoreo | `backend/src/handler_interacciones.py`, `backend/src/handler_notificador.py`, `infra/monitoring.tf`, `docs/MONITOREO.md` |

La infraestructura (`infra/`) y la documentación general se tocan entre los tres, según lo que cada cambio necesite.

Las fronteras no son rígidas: cuando alguien toca el área de otro, se revisa en el pull request.
Lo importante para la entrega es que el historial muestre commits reales de los tres.

## Antes de abrir un pull request

```bash
terraform fmt -recursive            # formato de los .tf
cd infra && terraform validate      # sintaxis de la infraestructura
python3 -m py_compile backend/src/*.py
./scripts/prueba_flujos.sh          # si cambiaste backend o infraestructura
```

## Reglas de seguridad

- Nunca se sube `terraform.tfstate`, `.env`, llaves `.pem` ni credenciales de AWS.
- Las contraseñas se guardan solo como hash PBKDF2; la llave de firma vive en Secrets Manager.
- Si alguien filtra una credencial por error: rotarla en AWS **antes** de reescribir el historial.
