"""Environment-backed configuration for provider adapters."""

from dataclasses import dataclass
import os
from urllib.parse import urlparse

from planificahoy.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class Settings:
    geocoding_base_url: str = "https://geocoding-api.open-meteo.com/v1"
    forecast_base_url: str = "https://api.open-meteo.com/v1"
    http_timeout_seconds: float = 10.0
    max_location_candidates: int = 5
    temperature_unit: str = "celsius"
    wind_speed_unit: str = "kmh"

    @classmethod
    def from_env(cls) -> "Settings":
        """Load configuration from environment variables with safe defaults."""

        defaults = cls()
        settings = cls(
            geocoding_base_url=os.getenv(
                "PLANIFICAHOY_GEOCODING_BASE_URL", defaults.geocoding_base_url
            ),
            forecast_base_url=os.getenv(
                "PLANIFICAHOY_FORECAST_BASE_URL", defaults.forecast_base_url
            ),
            http_timeout_seconds=_read_float(
                "PLANIFICAHOY_HTTP_TIMEOUT_SECONDS", defaults.http_timeout_seconds
            ),
            max_location_candidates=_read_int(
                "PLANIFICAHOY_MAX_LOCATION_CANDIDATES",
                defaults.max_location_candidates,
            ),
            temperature_unit=os.getenv(
                "PLANIFICAHOY_TEMPERATURE_UNIT", defaults.temperature_unit
            ),
            wind_speed_unit=os.getenv(
                "PLANIFICAHOY_WIND_SPEED_UNIT", defaults.wind_speed_unit
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        for label, value in (
            ("Geocoding", self.geocoding_base_url),
            ("Forecast", self.forecast_base_url),
        ):
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ConfigurationError(f"La URL base de {label} no es valida.")

        if self.http_timeout_seconds <= 0:
            raise ConfigurationError("El timeout HTTP debe ser mayor que cero.")
        if not 1 <= self.max_location_candidates <= 100:
            raise ConfigurationError(
                "La cantidad maxima de ubicaciones debe estar entre 1 y 100."
            )
        if self.temperature_unit != "celsius":
            raise ConfigurationError(
                "El modelo interno de esta fase requiere temperatura en Celsius."
            )
        if self.wind_speed_unit != "kmh":
            raise ConfigurationError(
                "El modelo interno de esta fase requiere viento en km/h."
            )


def _read_float(variable: str, default: float) -> float:
    raw_value = os.getenv(variable)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{variable} debe ser un numero.") from exc


def _read_int(variable: str, default: int) -> int:
    raw_value = os.getenv(variable)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{variable} debe ser un entero.") from exc
