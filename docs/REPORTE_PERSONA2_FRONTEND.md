# Reporte — Persona 2 (Frontend e integración)

## Archivos nuevos
- `src/planificahoy/frontend/index.html`
- `src/planificahoy/frontend/css/styles.css`
- `src/planificahoy/frontend/js/app.js`

## Cambio en backend (coordinado con Persona 1)
- `src/planificahoy/main.py`: se agregó `_mount_frontend()` que monta `/css` y `/js` como estáticos y sirve `index.html` en `/`. Es **aditivo**: las rutas de API se registran antes, así que `/health`, `/locations`, `/weather` y `/recommendation` mantienen prioridad. No se tocaron contratos ni servicios.

## Flujo implementado
`buscar ubicación → GET /locations → mostrar candidatos → seleccionar → elegir actividad → GET /recommendation → mostrar clima, nivel, resumen y motivos`.

## Decisiones de integración
- Monolito: el frontend se sirve desde el mismo FastAPI. Sin CORS. Todas las llamadas usan **rutas relativas** (`/locations`, `/recommendation`).
- Nunca se llama a Open-Meteo desde el frontend.
- No se duplicó `ACTIVITY_RULES` en JS: toda la lógica de evaluación vive en el backend.
- Las coordenadas y timezone se toman del candidato elegido, nunca escritas a mano.

## Manejo de errores y estados
- Lee el formato `{ "detail": "..." }` del backend y lo muestra tal cual.
- Estados de carga en búsqueda y evaluación.
- Protección contra doble envío (botones deshabilitados mientras carga).
- Respuestas vacías de `/locations` muestran mensaje claro.

## Accesibilidad
- El nivel (FAVORABLE/REGULAR/UNFAVORABLE) se comunica con **texto + ícono**, no solo color.
- Foco visible por teclado, `aria-live` en estados, soporte de `prefers-reduced-motion`, responsive hasta móvil.

## Pruebas
- 68 tests del backend siguen pasando tras el cambio en `main.py`.
- Smoke test: `/` devuelve HTML, `/css/styles.css` y `/js/app.js` responden 200, `/health` OK, `/locations` sin query devuelve 422 (validación intacta).

## Cómo correr
```bash
uvicorn planificahoy.main:app --reload
# abrir http://127.0.0.1:8000/
```

## Coordinaciones
- Persona 1: confirmado montaje de estáticos en `main.py`. Si en el futuro el frontend corre en otro origen, habría que habilitar CORS para ese origen específico.
- Persona 3/4: si se agrega una actividad nueva, debe existir primero en backend (Activity, reglas, tests) antes de sumarla al `<div class="activity-options">` del `index.html`.
