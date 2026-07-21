"""Open-Meteo adapters and translation to internal models."""

from collections.abc import Mapping, Sequence
from datetime import datetime
import math
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from planificahoy.config import Settings
from planificahoy.errors import (
    ExternalResponseError,
    ExternalServiceConnectionError,
    ExternalServiceError,
    ExternalServiceRateLimitError,
    ExternalServiceRequestError,
    ExternalServiceTimeoutError,
    ExternalServiceUnavailableError,
)
from planificahoy.models import LocationCandidate, WeatherSnapshot


class OpenMeteoGeocoder:
    """Adapter for Open-Meteo's Geocoding API."""

    def __init__(self, client: httpx.Client, settings: Settings) -> None:
        self._client = client
        self._url = f"{settings.geocoding_base_url.rstrip('/')}/search"
        self._max_candidates = settings.max_location_candidates

    def search(self, query: str) -> list[LocationCandidate]:
        payload = _get_json(
            self._client,
            self._url,
            params={
                "name": query,
                "count": self._max_candidates,
                "language": "es",
                "format": "json",
            },
        )

        raw_results = payload.get("results", [])
        if not _is_sequence(raw_results):
            raise ExternalResponseError(
                "El proveedor devolvio una lista de ubicaciones invalida."
            )

        candidates: list[LocationCandidate] = []
        for raw_candidate in raw_results:
            candidate = _require_mapping(raw_candidate, "ubicacion")
            admin_region = candidate.get("admin1")
            if admin_region is not None and not isinstance(admin_region, str):
                raise ExternalResponseError(
                    "El proveedor devolvio una region administrativa invalida."
                )

            candidates.append(
                LocationCandidate(
                    name=_require_text(candidate, "name"),
                    country=_require_text(candidate, "country"),
                    country_code=_require_text(candidate, "country_code").upper(),
                    admin_region=admin_region,
                    latitude=_require_number(candidate, "latitude"),
                    longitude=_require_number(candidate, "longitude"),
                    timezone=_require_text(candidate, "timezone"),
                )
            )
        return candidates


class OpenMeteoWeatherProvider:
    """Adapter for Open-Meteo's hourly Forecast API."""

    _VARIABLES = (
        "temperature_2m",
        "precipitation_probability",
        "wind_speed_10m",
    )

    def __init__(self, client: httpx.Client, settings: Settings) -> None:
        self._client = client
        self._url = f"{settings.forecast_base_url.rstrip('/')}/forecast"
        self._temperature_unit = settings.temperature_unit
        self._wind_speed_unit = settings.wind_speed_unit

    def get_weather(
        self, latitude: float, longitude: float, timezone: str
    ) -> WeatherSnapshot:
        payload = _get_json(
            self._client,
            self._url,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "hourly": ",".join(self._VARIABLES),
                "forecast_hours": 2,
                "temperature_unit": self._temperature_unit,
                "wind_speed_unit": self._wind_speed_unit,
                "timezone": timezone,
                "timeformat": "iso8601",
            },
        )

        hourly_units = _require_mapping(payload.get("hourly_units"), "hourly_units")
        _validate_units(hourly_units)
        hourly = _require_mapping(payload.get("hourly"), "hourly")

        times = _require_sequence(hourly, "time")
        temperatures = _require_sequence(hourly, "temperature_2m")
        precipitation_probabilities = _require_sequence(
            hourly, "precipitation_probability"
        )
        wind_speeds = _require_sequence(hourly, "wind_speed_10m")

        lengths = {
            len(times),
            len(temperatures),
            len(precipitation_probabilities),
            len(wind_speeds),
        }
        if lengths == {0} or len(lengths) != 1:
            raise ExternalResponseError(
                "Las series horarias del proveedor no estan alineadas."
            )

        response_timezone = _require_text(payload, "timezone")
        try:
            timezone_info = ZoneInfo(response_timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ExternalResponseError(
                "El proveedor devolvio una zona horaria invalida."
            ) from exc

        for raw_time, raw_temperature, raw_precipitation, raw_wind in zip(
            times,
            temperatures,
            precipitation_probabilities,
            wind_speeds,
            strict=True,
        ):
            if None in (
                raw_time,
                raw_temperature,
                raw_precipitation,
                raw_wind,
            ):
                continue

            timestamp = _parse_timestamp(raw_time, timezone_info)
            temperature = _number_value(raw_temperature, "temperature_2m")
            precipitation = _number_value(
                raw_precipitation, "precipitation_probability"
            )
            wind_speed = _number_value(raw_wind, "wind_speed_10m")

            if not 0 <= precipitation <= 100:
                raise ExternalResponseError(
                    "La probabilidad de precipitacion esta fuera de rango."
                )
            if wind_speed < 0:
                raise ExternalResponseError(
                    "La velocidad del viento no puede ser negativa."
                )

            return WeatherSnapshot(
                timestamp=timestamp,
                temperature_celsius=temperature,
                precipitation_probability_percent=precipitation,
                wind_speed_kmh=wind_speed,
            )

        raise ExternalResponseError(
            "El proveedor no devolvio una hora con datos meteorologicos completos."
        )


def _get_json(
    client: httpx.Client, url: str, *, params: Mapping[str, Any]
) -> Mapping[str, Any]:
    try:
        response = client.get(url, params=params)
    except httpx.TimeoutException as exc:
        raise ExternalServiceTimeoutError(
            "El proveedor meteorologico excedio el tiempo de espera."
        ) from exc
    except httpx.RequestError as exc:
        raise ExternalServiceConnectionError(
            "No fue posible conectar con el proveedor meteorologico."
        ) from exc

    if response.status_code == 400:
        raise ExternalServiceRequestError(
            "El proveedor rechazo la solicitud construida por el adaptador."
        )
    if response.status_code == 429:
        raise ExternalServiceRateLimitError(
            "El proveedor alcanzo temporalmente su limite de solicitudes."
        )
    if 500 <= response.status_code <= 599:
        raise ExternalServiceUnavailableError(
            "El proveedor meteorologico no esta disponible temporalmente."
        )
    if not 200 <= response.status_code <= 299:
        raise ExternalServiceError(
            "El proveedor meteorologico devolvio un error inesperado."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise ExternalResponseError(
            "El proveedor meteorologico no devolvio JSON valido."
        ) from exc
    return _require_mapping(payload, "respuesta")


def _validate_units(units: Mapping[str, Any]) -> None:
    expected = {
        "temperature_2m": "°C",
        "precipitation_probability": "%",
        "wind_speed_10m": "km/h",
    }
    for field, expected_unit in expected.items():
        if units.get(field) != expected_unit:
            raise ExternalResponseError(
                "El proveedor devolvio unidades meteorologicas inesperadas."
            )


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ExternalResponseError(
            f"El proveedor devolvio un campo {field} invalido."
        )
    return value


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _require_sequence(data: Mapping[str, Any], field: str) -> Sequence[Any]:
    value = data.get(field)
    if not _is_sequence(value):
        raise ExternalResponseError(
            f"El proveedor devolvio un campo {field} invalido."
        )
    return value


def _require_text(data: Mapping[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ExternalResponseError(
            f"El proveedor devolvio un campo {field} invalido."
        )
    return value.strip()


def _number_value(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExternalResponseError(
            f"El proveedor devolvio un campo {field} invalido."
        )
    number = float(value)
    if not math.isfinite(number):
        raise ExternalResponseError(
            f"El proveedor devolvio un campo {field} invalido."
        )
    return number


def _require_number(data: Mapping[str, Any], field: str) -> float:
    return _number_value(data.get(field), field)


def _parse_timestamp(value: Any, timezone_info: ZoneInfo) -> datetime:
    if not isinstance(value, str):
        raise ExternalResponseError(
            "El proveedor devolvio una fecha u hora invalida."
        )
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ExternalResponseError(
            "El proveedor devolvio una fecha u hora invalida."
        ) from exc
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone_info)
    return timestamp

