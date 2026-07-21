"""Small contracts implemented by external-service adapters."""

from typing import Protocol

from planificahoy.models import LocationCandidate, WeatherSnapshot


class Geocoder(Protocol):
    def search(self, query: str) -> list[LocationCandidate]:
        """Return structured candidates without choosing one automatically."""
        ...


class WeatherProvider(Protocol):
    def get_weather(
        self, latitude: float, longitude: float, timezone: str
    ) -> WeatherSnapshot:
        """Return the current or next available hourly weather snapshot."""
        ...

