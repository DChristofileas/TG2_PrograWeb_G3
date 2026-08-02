# Reporte Persona 4 — SecOps, documentación y evidencia

## Alcance completado

Se auditó la configuración, la integración externa, el frontend, FastAPI, las
pruebas y la documentación del repositorio. Este reporte solo registra
evidencia verificable desde el código y la configuración versionada; no afirma
capturas, accesos a Vercel ni ejecuciones que no estén adjuntas al PR.

## Auditoría de secretos y variables

- No se versionan `.env` reales: `.gitignore` ignora `.env` y `.env.*`, excepto
  `.env.example`.
- `.env.example` documenta únicamente `PLANIFICAHOY_GEOCODING_BASE_URL`,
  `PLANIFICAHOY_FORECAST_BASE_URL`, `PLANIFICAHOY_HTTP_TIMEOUT_SECONDS`,
  `PLANIFICAHOY_MAX_LOCATION_CANDIDATES`, `PLANIFICAHOY_TEMPERATURE_UNIT` y
  `PLANIFICAHOY_WIND_SPEED_UNIT`.
- Open-Meteo no requiere API key en esta aplicación. No existe
  `OPEN_METEO_API_KEY`, token, contraseña o credencial ficticia.
- El frontend llama solo a rutas relativas del backend, por lo que no recibe
  configuración privada ni credenciales.

## SecOps aplicado

- Validación de entradas con FastAPI y validación de las respuestas externas
  antes de formar los modelos internos.
- Traducción de errores externos a 502, 503 o 504 sin devolver tracebacks,
  paths locales ni cuerpos del proveedor.
- Headers añadidos a las respuestas: `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: strict-origin-when-cross-origin` y `Permissions-Policy`
  para deshabilitar cámara, geolocalización y micrófono.
- El mismo origen evita CORS innecesario. El frontend renderiza datos con
  `textContent`, mitigando inyección HTML en los valores recibidos.
- CSP se difiere de forma deliberada: `/docs` usa Swagger UI con scripts inline.
  Una política útil exige nonces o hashes y validación completa; no se agrega
  una CSP débil o que rompa la documentación académica.

## API pública y documentación

`/docs` y `/openapi.json` permanecen públicos. Son útiles para evaluación y
consumo de la API, y no exponen secretos. La atribución a Open-Meteo está
visible en el footer del frontend y documentada en el README.

## DevOps y Supabase

La configuración versionada muestra GitHub Actions con Python 3.12, instalación
bloqueada por `uv.lock` y job `pytest` en pull requests a `main` y pushes a
`main`. El flujo esperado es rama de funcionalidad, PR, `pytest`, Vercel
Preview y merge a Production. Supabase no aplica: el MVP no gestiona usuarios
ni persistencia.

## Checklist de requisitos y evidencia

| Requisito | Evidencia versionada | Validación pendiente en PR/entorno |
|---|---|---|
| Vercel / Production | `src/app.py` y `[tool.vercel]` en `pyproject.toml` | Abrir Preview y Production pública |
| API externa | Adaptadores Open-Meteo y pruebas con `MockTransport` | Flujo real desde Preview |
| GitHub / CI | `.github/workflows/tests.yml` | Check `pytest` verde del PR |
| README | `README.md` con producto, DevOps, SecOps y rollback | Revisión del equipo |
| Variables | `.env.example`, `config.py`, `.gitignore` | Confirmar variables de Vercel sin valores sensibles |
| DevOps | `CONTRIBUTING.md`, workflow y lockfile | PR y Preview revisados |
| SecOps | Middleware, pruebas de headers y manejo de errores | Verificar headers en Preview |
| Supabase no aplicable | README y este reporte | No requiere configuración externa |

## Verificación local requerida

```bash
uv sync --locked --all-extras
uv run python -m pytest
```

También se debe comprobar `/`, `/css/styles.css`, `/js/app.js`, `/docs`,
`/openapi.json`, una ruta inexistente y una solicitud inválida antes del merge.
