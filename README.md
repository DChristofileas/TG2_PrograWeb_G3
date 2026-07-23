# PlanificaHoy

PlanificaHoy es un proyecto universitario de Programación Web. El backend
permite buscar ubicaciones, consultar un resumen meteorológico horario mediante
Open-Meteo y generar una recomendación orientativa para una actividad.

## Alcance de esta fase

- Backend en Python y FastAPI.
- Geocodificación de texto mediante Open-Meteo Geocoding API.
- Consulta horaria mediante Open-Meteo Forecast API.
- Conversión del JSON externo a modelos internos estables.
- Recomendaciones para `football`, `running`, `picnic` y `cycling` mediante reglas internas.
- Frontend HTML, CSS y JavaScript servido desde la misma aplicación FastAPI.
- Pruebas unitarias y de endpoints sin conexión a Internet.
- Sin base de datos.

FastAPI se utiliza porque ofrece validación de parámetros, serialización JSON,
documentación OpenAPI automática y un cliente de pruebas sencillo, sin exigir
una arquitectura pesada.

## Arquitectura

```text
Frontend HTML/CSS/JavaScript
                 |
                 | fetch() a nuestro backend
                 v
          FastAPI / api/routes.py
                 |
                 v
                PlanningService
              /         |        \
             v          v         v
        Geocoder  WeatherProvider  RecommendationService
             ^          ^         |
             |          |         v
 OpenMeteoGeocoder  OpenMeteoWeatherProvider
             |          |    reglas centralizadas por actividad
             +----+-----+
                  v
              Open-Meteo
```

El frontend nunca consulta Open-Meteo directamente. `PlanningService` tampoco
conoce FastAPI, HTTPX, URLs, autenticación ni nombres de campos externos.
`main.py` es el punto de composición que conecta manualmente los puertos con sus
implementaciones.

`RecommendationService` conoce únicamente `WeatherSnapshot`, actividades,
niveles y reglas internas. No importa FastAPI, HTTPX ni adaptadores externos.

Los adaptadores realizan llamadas HTTP síncronas y las rutas se definen como
funciones síncronas; FastAPI las ejecuta en su pool de hilos y evita bloquear su
bucle asíncrono.

## Flujo de datos

1. El cliente solicita `GET /locations?query=San José`.
2. FastAPI valida la entrada y llama a `PlanningService`.
3. El servicio usa el contrato `Geocoder`.
4. `OpenMeteoGeocoder` consulta Open-Meteo y convierte cada resultado a
   `LocationCandidate`.
5. El cliente selecciona explícitamente San José, Costa Rica. El backend no
   elige automáticamente el primer resultado.
6. El cliente envía sus coordenadas y zona horaria a `GET /weather`.
7. `PlanningService` usa el contrato `WeatherProvider`.
8. `OpenMeteoWeatherProvider` solicita dos horas de pronóstico y selecciona la
   primera con los tres indicadores completos: la hora actual o la próxima
   disponible.
9. El adaptador devuelve un `WeatherSnapshot`; FastAPI lo serializa como JSON.
10. Para `/recommendation`, el mismo snapshot se entrega a
    `RecommendationService`, sin efectuar una segunda consulta meteorológica.
11. El servicio aplica las reglas de la actividad y genera un `Recommendation`.
12. FastAPI devuelve el clima y la recomendación juntos.

El JSON completo de Open-Meteo no atraviesa el adaptador.

## API externa

PlanificaHoy utiliza los endpoints públicos:

- Geocoding: `GET https://geocoding-api.open-meteo.com/v1/search`
- Forecast: `GET https://api.open-meteo.com/v1/forecast`

La consulta de Forecast solicita únicamente:

- `temperature_2m`, convertido a `temperature_celsius`;
- `precipitation_probability`, convertido a
  `precipitation_probability_percent`;
- `wind_speed_10m`, convertido a `wind_speed_kmh`.

Las unidades se solicitan explícitamente como Celsius, porcentaje y km/h. La
zona horaria proviene del candidato seleccionado y el timestamp de salida
incluye su desplazamiento UTC.

Documentación oficial:

- [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api)
- [Open-Meteo Forecast API](https://open-meteo.com/en/docs)

## Sistema de recomendaciones

`RecommendationService` transforma un `WeatherSnapshot` y una actividad en una
recomendación determinista. Las actividades disponibles son:

- `football`;
- `running`;
- `picnic`;
- `cycling`.

Cada actividad utiliza exactamente las mismas variables:

- `temperature_celsius`;
- `precipitation_probability_percent`;
- `wind_speed_kmh`.

Los niveles posibles son:

- `FAVORABLE`: las tres variables están en sus rangos favorables;
- `REGULAR`: no hay condiciones desfavorables, pero existe una advertencia;
- `UNFAVORABLE`: existe al menos una condición desfavorable.

Una condición desfavorable domina cualquier advertencia. Si no hay condiciones
desfavorables, una advertencia domina las condiciones favorables.

### Umbrales del prototipo

| Actividad | Variable | FAVORABLE | REGULAR | UNFAVORABLE |
|---|---|---|---|---|
| Football | Temperatura | `12 ≤ T ≤ 28 °C` | `5 ≤ T < 12` o `28 < T ≤ 34 °C` | `T < 5` o `T > 34 °C` |
| Football | Precipitación | `P < 40 %` | `40 ≤ P < 75 %` | `P ≥ 75 %` |
| Football | Viento | `V < 25 km/h` | `25 ≤ V < 40 km/h` | `V ≥ 40 km/h` |
| Running | Temperatura | `8 ≤ T ≤ 24 °C` | `0 ≤ T < 8` o `24 < T ≤ 30 °C` | `T < 0` o `T > 30 °C` |
| Running | Precipitación | `P < 40 %` | `40 ≤ P < 75 %` | `P ≥ 75 %` |
| Running | Viento | `V < 25 km/h` | `25 ≤ V < 40 km/h` | `V ≥ 40 km/h` |
| Picnic | Temperatura | `15 ≤ T ≤ 28 °C` | `10 ≤ T < 15` o `28 < T ≤ 32 °C` | `T < 10` o `T > 32 °C` |
| Picnic | Precipitación | `P < 25 %` | `25 ≤ P < 55 %` | `P ≥ 55 %` |
| Picnic | Viento | `V < 20 km/h` | `20 ≤ V < 35 km/h` | `V ≥ 35 km/h` |
| Cycling | Temperatura | `10 ≤ T ≤ 26 °C` | `5 ≤ T < 10` o `26 < T ≤ 32 °C` | `T < 5` o `T > 32 °C` |
| Cycling | Precipitación | `P < 30 %` | `30 ≤ P < 65 %` | `P ≥ 65 %` |
| Cycling | Viento | `V < 20 km/h` | `20 ≤ V < 35 km/h` | `V ≥ 35 km/h` |

Los umbrales están definidos en una única tabla inmutable dentro de
`recommendation_service.py`. Agregar otra actividad con el mismo algoritmo
requiere incorporar su nombre y sus umbrales, no crear otra clase evaluadora.

> Las recomendaciones son orientativas y se generan mediante reglas internas
> del prototipo PlanificaHoy. No constituyen alertas meteorológicas oficiales ni
> recomendaciones médicas.

## Endpoints de PlanificaHoy

### `GET /health`

Comprueba que el backend está disponible.

```json
{"status": "ok"}
```

### `GET /locations?query=San%20José`

Devuelve cero o más candidatos. No selecciona uno automáticamente.

```json
[
  {
    "name": "San José",
    "country": "Costa Rica",
    "country_code": "CR",
    "admin_region": "San José",
    "latitude": 9.93333,
    "longitude": -84.08333,
    "timezone": "America/Costa_Rica"
  }
]
```

### `GET /weather`

Parámetros obligatorios: `latitude`, `longitude` y `timezone`.

```json
{
  "timestamp": "2026-07-20T18:00:00-06:00",
  "temperature_celsius": 24.2,
  "precipitation_probability_percent": 70.0,
  "wind_speed_kmh": 12.5
}
```

Los valores anteriores ilustran la estructura; el pronóstico real cambia con
la hora de la consulta.

### `GET /recommendation`

Parámetros obligatorios: `latitude`, `longitude`, `timezone` y `activity`. La
actividad debe ser `football`, `running`, `picnic` o `cycling`.

```json
{
  "weather": {
    "timestamp": "2026-07-20T18:00:00-06:00",
    "temperature_celsius": 20.8,
    "precipitation_probability_percent": 96.0,
    "wind_speed_kmh": 7.9
  },
  "recommendation": {
    "activity": "football",
    "level": "UNFAVORABLE",
    "summary": "Existe al menos una condición desfavorable para realizar esta actividad.",
    "reasons": [
      "La probabilidad de precipitación de 96 % se considera desfavorable para esta actividad."
    ]
  }
}
```

El endpoint consulta el pronóstico una sola vez y usa el mismo
`WeatherSnapshot` tanto en la respuesta como en la evaluación.

La documentación interactiva de FastAPI queda disponible en `/docs` y el
esquema OpenAPI en `/openapi.json`.

## Configuración

La aplicación tiene valores públicos seguros por defecto. Se pueden reemplazar
desde variables de entorno:

| Variable | Propósito | Valor predeterminado |
|---|---|---|
| `PLANIFICAHOY_GEOCODING_BASE_URL` | URL base de Geocoding | `https://geocoding-api.open-meteo.com/v1` |
| `PLANIFICAHOY_FORECAST_BASE_URL` | URL base de Forecast | `https://api.open-meteo.com/v1` |
| `PLANIFICAHOY_HTTP_TIMEOUT_SECONDS` | Timeout de HTTPX | `10` |
| `PLANIFICAHOY_MAX_LOCATION_CANDIDATES` | Máximo de resultados | `5` |
| `PLANIFICAHOY_TEMPERATURE_UNIT` | Unidad contractual | `celsius` |
| `PLANIFICAHOY_WIND_SPEED_UNIT` | Unidad contractual | `kmh` |

`.env.example` documenta estas variables y no contiene secretos. Esta versión
no carga archivos `.env` automáticamente; las variables se suministran desde el
shell o la plataforma de despliegue. Las URLs son configuración interna y nunca
parámetros proporcionados por el usuario.

## Autenticación con APIs externas

### 1. API pública sin autenticación

Es el caso actual. La Open-Meteo Free API usada por PlanificaHoy no requiere API
key, Bearer Token, OAuth, usuario ni contraseña. Por eso el proyecto no define
`OPEN_METEO_API_KEY` ni envía credenciales ficticias.

### 2. API Key

Es una clave emitida por un proveedor y enviada en un header o parámetro, según
su documentación. Si un proveedor futuro la necesita, su adaptador la recibirá
desde configuración respaldada por una variable de entorno.

### 3. Bearer Token

Normalmente se envía en el encabezado HTTP:

```text
Authorization: Bearer <token>
```

El token se mantendría únicamente en el backend y el adaptador correspondiente
construiría el encabezado.

### 4. OAuth 2.0

Se utiliza cuando una aplicación necesita autorización delegada o acceso en
nombre de un usuario. Su flujo, almacenamiento y renovación de tokens
pertenecerían a la infraestructura del proveedor, no al frontend ni a la lógica
meteorológica.

Cualquier secreto futuro se almacenará en variables de entorno o en el gestor
de secretos de la plataforma. Nunca se escribirá directamente en el código, el
repositorio o JavaScript del navegador.

## Manejo de errores y seguridad HTTP

- HTTPX utiliza un timeout explícito.
- Los valores del usuario se envían mediante `params`; no se concatenan en URLs.
- El adaptador comprueba el código HTTP antes de interpretar el cuerpo.
- `400` del proveedor se traduce en `502`, porque indica una solicitud inválida
  construida por la integración.
- `429`, errores de conexión y `5xx` se traducen en `503`.
- Los timeouts se traducen en `504`.
- JSON no válido, estructura inesperada, campos faltantes, series desalineadas o
  unidades incorrectas se traducen en `502`.
- FastAPI responde `422` cuando los parámetros HTTP no cumplen su esquema.
- Una actividad vacía o no soportada recibe `422` con las opciones válidas.
- Un `WeatherSnapshot` internamente inválido no expone trazas y recibe una
  respuesta genérica `500`.
- La aplicación no devuelve trazas ni cuerpos completos del proveedor.
- Latitud, longitud, zona horaria y valores meteorológicos se validan antes de
  producir el modelo interno.
- No se aceptan URLs desde el cliente ni se siguen redirecciones externas.

Si el frontend se aloja en otro origen, se añadirá posteriormente CORS con una
lista explícita de orígenes; no se habilita un comodín en esta fase.

## SOLID aplicado

- **S — Single Responsibility:** rutas para HTTP, servicio para coordinación,
  adaptadores para proveedores, configuración para entorno, modelos para datos y
  `RecommendationService` exclusivamente para evaluación.
- **O — Open/Closed:** otro proveedor puede implementar los mismos puertos sin
  cambiar `PlanningService`; una actividad similar se agrega principalmente en
  la tabla de reglas.
- **L — Liskov Substitution:** todo `WeatherProvider` debe conservar tipos,
  unidades y significado temporal de `WeatherSnapshot`.
- **I — Interface Segregation:** `Geocoder` y `WeatherProvider` son contratos
  pequeños e independientes.
- **D — Dependency Inversion:** `PlanningService` depende de esos contratos y
  recibe implementaciones por constructor. También recibe el servicio de
  recomendaciones mediante inyección explícita.

## Patrones utilizados

- Adapter para aislar Open-Meteo.
- Dependency Injection manual en `main.py`.
- Application Service mediante `PlanningService`.
- Ports and Adapters de forma ligera mediante `typing.Protocol`.
- Reglas configurables mediante una tabla inmutable por actividad.

No se utilizan Strategy, Factory, Repository, ORM, Circuit Breaker, contenedor
DI ni microservicios.

## Instalación

Requiere Python 3.11 o posterior.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Ejecución

```bash
uvicorn planificahoy.main:app --app-dir src --reload
```

Comprobaciones manuales:

```bash
curl http://127.0.0.1:8000/health

curl --get http://127.0.0.1:8000/locations \
  --data-urlencode "query=San José"

curl --get http://127.0.0.1:8000/weather \
  --data-urlencode "latitude=9.93333" \
  --data-urlencode "longitude=-84.08333" \
  --data-urlencode "timezone=America/Costa_Rica"

curl --get http://127.0.0.1:8000/recommendation \
  --data-urlencode "latitude=9.93333" \
  --data-urlencode "longitude=-84.08333" \
  --data-urlencode "timezone=America/Costa_Rica" \
  --data-urlencode "activity=football"
```

Las coordenadas del último comando deben sustituirse por las devueltas para el
candidato elegido; no deben suponerse ni seleccionar automáticamente la primera
ubicación.

## Pruebas

```bash
python -m pytest
```

Las pruebas unitarias utilizan `httpx.MockTransport`, proveedores falsos y el
`TestClient` de FastAPI. Las pruebas de `RecommendationService` no importan
FastAPI, HTTPX ni Open-Meteo. Ninguna prueba automatizada realiza llamadas a
Internet. La conexión real se comprueba manualmente levantando el backend y
ejecutando el flujo anterior.

La suite incluye casos límite de coordenadas, zonas horarias, actividades,
respuestas incompletas del proveedor, valores meteorológicos fuera de rango y
errores HTTP externos poco comunes.

GitHub Actions ejecuta la misma suite automáticamente en cada push a `main` y en
cada pull request dirigido a esa rama.

## Trabajo colaborativo

Las instrucciones para preparar el entorno, crear ramas, escribir commits y
abrir pull requests están en [CONTRIBUTING.md](CONTRIBUTING.md). El flujo
recomendado consiste en trabajar en ramas pequeñas y solicitar revisión antes de
integrar cambios en `main`.

El repositorio incluye una plantilla de pull request y una validación automática
con Python 3.12. Los archivos locales, secretos, entornos virtuales, cachés,
configuración de editores y logs están excluidos mediante `.gitignore`.

## Frontend

El frontend estático se sirve desde la misma aplicación FastAPI:

```text
src/planificahoy/frontend/
├── index.html
├── css/styles.css
└── js/app.js
```

`app.js` consumirá exclusivamente `/locations`, `/weather` y `/recommendation`
del backend.

## Fuera de alcance deliberadamente

- selección de una hora por el usuario;
- traducción o personalización avanzada de mensajes;
- algoritmos distintos por actividad mediante Strategy;
- autenticación de usuarios;
- base de datos, historial, favoritos o preferencias;
- caché, reintentos automáticos y persistencia;
- despliegue y configuración CORS entre orígenes distintos.

## Atribución

Datos meteorológicos y geocodificación obtenidos mediante
[Open-Meteo](https://open-meteo.com/). Antes de una publicación o uso distinto
al académico se deben revisar también sus condiciones de uso y las licencias de
las fuentes de datos seleccionadas por el servicio.
