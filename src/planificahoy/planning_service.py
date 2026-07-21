"""Application service that coordinates PlanificaHoy use cases."""

import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from planificahoy.errors import InvalidInputError
from planificahoy.models import (
    Activity,
    LocationCandidate,
    RecommendationResult,
    WeatherSnapshot,
)
from planificahoy.ports import Geocoder, WeatherProvider
from planificahoy.recommendation_service import RecommendationService


class PlanningService:
    def __init__(
        self,
        geocoder: Geocoder,
        weather_provider: WeatherProvider,
        recommendation_service: RecommendationService,
    ) -> None:
        self._geocoder = geocoder
        self._weather_provider = weather_provider
        self._recommendation_service = recommendation_service

    def search_locations(self, query: str) -> list[LocationCandidate]:
        normalized_query = query.strip()
        if len(normalized_query) < 2:
            raise InvalidInputError(
                "La ubicacion debe contener al menos dos caracteres."
            )
        if len(normalized_query) > 100:
            raise InvalidInputError(
                "La ubicacion no puede superar los 100 caracteres."
            )
        return self._geocoder.search(normalized_query)

    def get_weather(
        self, latitude: float, longitude: float, timezone: str
    ) -> WeatherSnapshot:
        if not math.isfinite(latitude) or not -90 <= latitude <= 90:
            raise InvalidInputError("La latitud debe estar entre -90 y 90.")
        if not math.isfinite(longitude) or not -180 <= longitude <= 180:
            raise InvalidInputError("La longitud debe estar entre -180 y 180.")

        normalized_timezone = timezone.strip()
        if not normalized_timezone or len(normalized_timezone) > 100:
            raise InvalidInputError("La zona horaria no es valida.")
        try:
            ZoneInfo(normalized_timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise InvalidInputError("La zona horaria no es valida.") from exc

        return self._weather_provider.get_weather(
            latitude=latitude,
            longitude=longitude,
            timezone=normalized_timezone,
        )

    def get_recommendation(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        activity: Activity | str,
    ) -> RecommendationResult:
        selected_activity = self._recommendation_service.parse_activity(activity)
        snapshot = self.get_weather(latitude, longitude, timezone)
        recommendation = self._recommendation_service.evaluate(
            snapshot, selected_activity
        )
        return RecommendationResult(
            weather=snapshot,
            recommendation=recommendation,
        )
