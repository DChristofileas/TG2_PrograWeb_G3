# Reporte Persona 2 — Frontend de producción (Trabajo Grupal #2)

**Rama:** `feature/frontend-production` (PR #5, fusionado en `main`)
**Archivos modificados:** `src/planificahoy/frontend/index.html`, `src/planificahoy/frontend/css/styles.css`
**Archivos sin cambios:** `src/planificahoy/frontend/js/app.js` (ya cumplía los criterios de producción)

---

## 1. Auditoría inicial (estado de `main` antes de la rama)

Se sincronizó `main`, se ejecutó la suite (106 tests passing) y se revisó Production (`https://planificahoy.vercel.app/`). Hallazgos:

| Criterio del rol | Estado encontrado |
| --- | --- |
| Loading claro | ✅ Ya existía ("Buscando ubicaciones…", "Consultando el pronóstico…") con `role="status"` y `aria-live="polite"` |
| Evitar dobles envíos | ✅ Flags `state.searching` / `state.evaluating` + botones deshabilitados durante el fetch |
| Estados vacíos | ✅ "No se encontraron ubicaciones. Prueba otro nombre." |
| Errores amigables | ✅ `readError()` lee `detail` del backend; mensajes genéricos sin trazas técnicas; fallback si el servidor no responde |
| Resultado legible | ✅ Banner de nivel (icono + texto, no solo color), grid de condiciones, lista de motivos |
| Responsive | ✅ `max-width` + media query 480px + grid `auto-fit`; sin scroll horizontal |
| Accesibilidad | ✅ Label `sr-only`, `radiogroup`, `focus-visible`, navegación por teclado (Enter busca), `prefers-reduced-motion` |
| Seguridad (XSS) | ✅ Todo dato externo se inserta con `textContent` / `createElement`; cero `innerHTML` |
| **Atribución Open-Meteo** | ❌ Faltaba (requerida por licencia CC BY 4.0 y por el Definition of Done) |
| **Meta description** | ❌ Faltaba |
| **Favicon** | ❌ Faltaba (el navegador pedía `/favicon.ico` → 404 en consola) |
| Disclaimer | ⚠️ Existía, pero solo visible tras evaluar (dentro de la tarjeta de resultado) |

## 2. Cambios realizados

### Atribución Open-Meteo (requisito de licencia)
Se agregó un `<footer>` siempre visible con el enlace requerido por la licencia de Open-Meteo (CC BY 4.0 exige un enlace junto a donde se muestran los datos):

> Datos meteorológicos de [Open-Meteo.com](https://open-meteo.com/) (licencia CC BY 4.0). Las recomendaciones son orientativas.

- El enlace usa `target="_blank" rel="noopener noreferrer"` (buena práctica de seguridad para enlaces externos).
- El disclaimer "orientativo" ahora también es permanente (antes solo aparecía en el resultado; se mantiene además el de la tarjeta).
- Estilo discreto: mismo tono `--muted` del diseño existente, sin competir con el contenido.

### Favicon y metadata
- **Favicon:** solución mínima con SVG inline como data URI en `<link rel="icon">` (emoji ⛅). Al declarar el icono, los navegadores dejan de pedir `/favicon.ico`, por lo que **no se necesitó tocar el backend** ni agregar rutas/archivos binarios. Elimina el 404 de consola.
- **`<meta name="description">`:** agregada (describe producto y actividades).
- **`<meta name="theme-color">`:** `#2a6df4` (color de marca ya definido en CSS) para la barra del navegador móvil.
- `<title>` y `viewport` ya existían y se conservaron (el test `test_root_serves_frontend_index` valida `<title>PlanificaHoy`).

### CSS
- Se agregó únicamente `.site-footer` reutilizando variables existentes (`--muted`, `--brand-ink`). Sin cambios al resto del diseño.

## 3. Decisión assets/CDN
**Se mantiene FastAPI + StaticFiles (no se mueven los assets a `public/`).** Razones:

1. El modelo de mismo origen ya funciona en Production y evita CORS (decisión de arquitectura de Persona 1).
2. Los assets están incluidos en el wheel vía `package-data` en `pyproject.toml`; moverlos rompería esa configuración y los tests de `/css/styles.css` y `/js/app.js`.
3. Para el alcance del proyecto (3 archivos estáticos pequeños) un CDN no aporta beneficio medible y sí riesgo de romper rutas antes de la entrega.

## 4. Seguridad
- Se mantiene la política de `textContent` para todo dato externo (sin `innerHTML`).
- Único elemento nuevo con enlace externo: la atribución, con `rel="noopener noreferrer"`.
- No se agregaron dependencias, secretos ni variables.

## 5. Tests
- Suite completa tras los cambios: **106 passed** (misma cifra que `main`).
- Check obligatorio `pytest` en verde en el PR #5 (CI con Python 3.12 + `uv.lock`).
- Los cambios son aditivos en HTML/CSS; `app.js` y contratos intactos.

## 6. Pruebas manuales (Production)

El PR #5 se fusionó con 3 checks en verde (incluido `pytest`) y el QA manual se
realizó directamente sobre Production tras el despliegue automático:

- [x] Búsqueda "San José" → candidatos → selección → actividad → recomendación
- [x] Error controlado: búsqueda de 1 carácter y término inexistente muestran mensajes amigables
- [x] Footer con atribución Open-Meteo visible en desktop y móvil (DevTools, Ctrl+Shift+M)
- [x] Favicon visible en la pestaña; consola sin 404 de `/favicon.ico` ni errores
- [x] Sin scroll horizontal en 360px de ancho
- [x] Navegación por teclado: Tab por input, botón, candidatos, chips y enlace del footer

**Validado en:** Production `https://planificahoy.vercel.app/` (PR #5, commit `d5ab39b`, merge `3ac69f3`, 3 checks ✅, deploy Vercel "Ready")

## 7. Riesgos y cambios que afectan a otros
- **Persona 4:** debe documentar la atribución Open-Meteo en el README (coordinación prevista en su rol). Este PR no toca README ni `docs/` compartidos, solo agrega este reporte.
- **Persona 1:** sin cambios de contratos, backend, rutas ni `app.js`. Nada que coordinar.
- **Persona 3:** el nombre del check `pytest` y la suite no se tocan.
- Riesgo residual: ninguno identificado; los cambios son estáticos y aditivos.
