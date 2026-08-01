# Reporte Persona 3 - CI/CD, reproducibilidad y QA de produccion

## Rama

Rama esperada para el PR: `feature/production-qa`.

## Auditoria inicial

Estado revisado antes de modificar:

- `.github/workflows/tests.yml` existia con job `pytest`.
- `.python-version` fija Python `3.12`.
- `pyproject.toml` define dependencias y extras de desarrollo.
- `uv.lock` existe y debe ser la fuente de reproducibilidad para CI.
- Suite local inicial: `106 passed`.
- `uv` no estaba instalado en el entorno local usado para esta revision, por lo
  que la validacion local directa de `uv sync` queda para CI o para un entorno
  con `uv` instalado.

## Cambios de CI

El workflow `Tests` mantiene el check obligatorio:

```text
pytest
```

Se cambio la instalacion de dependencias para usar el lockfile:

```text
checkout
setup-python desde .python-version
setup-uv con cache por uv.lock
uv sync --locked --all-extras
uv run python -m pytest
```

Esto evita que CI resuelva versiones diferentes a las registradas en `uv.lock`.
No se actualizaron dependencias de forma arbitraria.

## Uso de uv.lock

`uv.lock` queda como contrato de instalacion reproducible. La suite local puede
seguir ejecutandose con `python -m pytest` si el entorno ya esta preparado, pero
CI instala con `uv sync --locked --all-extras`.

Comando recomendado para reproducir CI en una maquina con `uv` instalado:

```bash
uv sync --locked --all-extras
uv run python -m pytest
```

## Smoke tests

La suite obligatoria `pytest` no depende de Internet ni de Open-Meteo. Los smoke
tests externos se mantienen separados para no volver fragil el required check.

Smoke minimo para Preview y Production:

```text
GET /
GET /health
GET /css/styles.css
GET /js/app.js
```

Validacion manual adicional:

```text
1. Abrir la URL desplegada.
2. Buscar "San Jose" o "San Jose, Costa Rica".
3. Seleccionar una ubicacion.
4. Evaluar una actividad, incluyendo `cycling`.
5. Confirmar que se muestran clima, nivel, resumen y motivos.
```

`/locations` y `/recommendation` consumen Open-Meteo. Deben probarse en QA
manual, pero no como paso obligatorio de CI para evitar fallos por red,
intermitencia externa o rate limiting.

## QA Preview

Checklist para cada PR:

- [ ] Vercel Preview en estado Ready.
- [ ] URL Preview registrada en el PR: `pendiente`.
- [ ] `/` carga el frontend.
- [ ] `/health` responde `{"status":"ok"}`.
- [ ] `/css/styles.css` responde 200.
- [ ] `/js/app.js` responde 200.
- [ ] Consola del navegador sin errores.
- [ ] Busqueda de ubicacion funciona.
- [ ] Recomendacion funciona para `cycling`.
- [ ] Frontend consume solo rutas del backend, no Open-Meteo directamente.
- [ ] No hay secretos visibles en frontend ni en logs.

## QA Production

URL actual de Production:

```text
https://planificahoy.vercel.app/
```

Checklist post-merge:

- [ ] Deploy de Production en estado Ready.
- [ ] `/` carga correctamente.
- [ ] `/health` responde `{"status":"ok"}`.
- [ ] Assets CSS/JS cargan correctamente.
- [ ] Flujo real: ubicacion -> actividad -> recomendacion.
- [ ] `cycling` disponible y funcional.
- [ ] Mensajes de error son amigables si no hay datos o si falla el proveedor.
- [ ] Atribucion de Open-Meteo visible.

## Cold start

No se agrega cache, Redis ni circuit breaker en esta etapa. Para el MVP, el
objetivo es observar y documentar:

- primer request tras inactividad;
- requests posteriores;
- si el tiempo de respuesta sigue siendo aceptable para una demo academica.

Resultado de medicion: pendiente de completar en Preview/Production durante el
QA del PR.

## Supply chain basica

Controles aplicados o verificados:

- Dependencias Python declaradas en `pyproject.toml`.
- Resolucion de dependencias versionada en `uv.lock`.
- CI instala con `uv sync --locked --all-extras`.
- Python se obtiene desde `.python-version`.
- El check obligatorio `pytest` conserva su nombre.
- No se agregaron secretos, API keys ni tokens.
- `.env.example` sigue siendo plantilla sin valores sensibles.
- Supabase no se agrega porque el MVP no persiste datos.
- No se introducen dependencias nuevas para QA.

Riesgo residual: Open-Meteo puede fallar o responder lento desde Production.
Ese riesgo se valida con smoke manual, no en el check obligatorio.

## Asuntos para Persona 1

- Confirmar que el required check configurado en GitHub sigue apuntando al job
  `pytest` despues del PR.
- Confirmar que Vercel usa Python 3.12 y el entrypoint `src.app:app`.
- Completar en el PR la URL Preview y el resultado de cold start.
