"""Provider-independent data models used by the application."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Activity(StrEnum):
    FOOTBALL = "football"
    RUNNING = "running"
    PICNIC = "picnic"


class RecommendationLevel(StrEnum):
    FAVORABLE = "FAVORABLE"
    REGULAR = "REGULAR"
    UNFAVORABLE = "UNFAVORABLE"


@dataclass(frozen=True, slots=True)
class LocationCandidate:
    """A location returned by a geocoding provider."""

    name: str
    country: str
    country_code: str
    admin_region: str | None
    latitude: float
    longitude: float
    timezone: str


@dataclass(frozen=True, slots=True)
class WeatherSnapshot:
    """Weather values for one forecast hour, in the application's units."""

    timestamp: datetime
    temperature_celsius: float
    precipitation_probability_percent: float
    wind_speed_kmh: float


@dataclass(frozen=True, slots=True)
class Recommendation:
    """An orientation generated from PlanificaHoy's internal rules."""

    activity: Activity
    level: RecommendationLevel
    summary: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    """Weather and its recommendation, produced from a single snapshot."""

    weather: WeatherSnapshot
    recommendation: Recommendation
