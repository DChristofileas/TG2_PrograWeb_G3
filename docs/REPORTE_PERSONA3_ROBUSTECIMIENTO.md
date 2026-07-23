# Reporte - Persona 3 (Robustecimiento funcional y pruebas)

## Objetivo

uvicorn planificahoy.main:app --app-dir src --reload

Fortalecer el comportamiento del proyecto con una ampliacion controlada de
actividades, mas pruebas de casos limite y mejoras de validacion sin cambiar los
endpoints actuales ni el modelo meteorologico interno.

## Actividad agregada

Se agrego `cycling` como nueva actividad soportada. Ciclismo usa los mismos tres
datos que ya entrega Open-Meteo y que ya existen en `WeatherSnapshot`:

- `temperature_celsius`;
- `precipitation_probability_percent`;
- `wind_speed_kmh`.

No se agregaron campos nuevos al modelo, no se cambio el endpoint
`/recommendation` y no se agregaron llamadas adicionales a Open-Meteo.

## Umbrales de ciclismo

| Variable      | FAVORABLE             | REGULAR                                | UNFAVORABLE                |
| ------------- | --------------------- | -------------------------------------- | -------------------------- |
| Temperatura   | `10 <= T <= 26 °C` | `5 <= T < 10` o `26 < T <= 32 °C` | `T < 5` o `T > 32 °C` |
| Precipitacion | `P < 30 %`          | `30 <= P < 65 %`                     | `P >= 65 %`              |
| Viento        | `V < 20 km/h`       | `20 <= V < 35 km/h`                  | `V >= 35 km/h`           |

La regla es mas sensible al viento y a la precipitacion que futbol/running,
porque en ciclismo afectan estabilidad, frenado, visibilidad y superficie.

## Archivos modificados

- `src/planificahoy/models.py`: se agrego `Activity.CYCLING`.
- `src/planificahoy/recommendation_service.py`: se agregaron los umbrales de
  ciclismo en `ACTIVITY_RULES`.
- `src/planificahoy/planning_service.py`: se aclaro el mensaje de zona horaria
  invalida con un ejemplo de identificador.
- `src/planificahoy/frontend/index.html`: se agrego la opcion Ciclismo.
- `src/planificahoy/frontend/js/app.js`: se reemplazo el render de candidatos
  con `innerHTML` por nodos creados con `textContent`.
- `tests/test_recommendation_service.py`: pruebas de ciclismo y parseo de
  actividad con mayusculas/espacios.
- `tests/test_planning_service.py`: pruebas de zona horaria, coordenadas no
  finitas, busqueda larga y no llamadas innecesarias cuando la actividad es
  invalida.
- `tests/test_open_meteo_adapter.py`: pruebas para respuestas incompletas,
  series desalineadas, valores meteorologicos fuera de rango, timezone invalido
  del proveedor y errores HTTP poco comunes.
- `tests/test_routes.py`: prueba de `/recommendation` con `activity=cycling` y
  mensaje claro para zona horaria invalida.
- `README.md`: actividades, umbrales, frontend actual y nota de robustez.

## Casos limite cubiertos

- `timezone` con espacios externos, por ejemplo `" America/Costa_Rica "`.
- `timezone` vacio, solo espacios o invalido.
- latitud y longitud fuera de rango.
- latitud y longitud `nan`, `inf` y `-inf` directamente en `PlanningService`.
- busqueda con mas de 100 caracteres.
- actividad con mayusculas y espacios en el servicio, por ejemplo
  `" CYCLING "`.
- actividad invalida rechazada antes de llamar al proveedor meteorologico.
- Open-Meteo con `hourly_units` faltante.
- Open-Meteo con `hourly` faltante.
- series horarias con longitudes distintas.
- primera hora incompleta y segunda hora completa.
- todas las horas incompletas.
- precipitacion menor que `0` o mayor que `100`.
- viento negativo.
- timezone invalido devuelto por Open-Meteo.
- errores HTTP externos poco comunes como `401` y `418`.

## Seguridad y consistencia

El frontend ya no usa `innerHTML` para pintar candidatos devueltos por
`/locations`. Los textos de ubicacion provienen de un proveedor externo, por lo
que ahora se insertan con `textContent`.

Los errores externos siguen traduciendose a respuestas controladas. Los casos de
snapshot meteorologico invalido mantienen una respuesta generica para no exponer
detalles internos.

## Contratos mantenidos

- `GET /health` se mantiene sin cambios.
- `GET /locations` se mantiene sin cambios.
- `GET /weather` se mantiene sin cambios.
- `GET /recommendation` se mantiene con los mismos parametros; solo se agrego
  `cycling` como valor valido para `activity`.
- `WeatherSnapshot` no cambio.
- El frontend sigue consumiendo solo el backend, no Open-Meteo directamente.

## Coordinacion

Persona 2 debe saber que el frontend ya incluye Ciclismo y que el render de
candidatos se hizo mas seguro sin cambiar el flujo visual. Persona 4 debe tomar
en cuenta que README ya incluye `cycling`, pero si documenta la entrega final
debe mencionar esta nueva actividad y las pruebas de robustez.
