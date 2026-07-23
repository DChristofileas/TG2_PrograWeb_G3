from datetime import datetime
import math
from zoneinfo import ZoneInfo

import pytest

from planificahoy.errors import InvalidInputError, UnsupportedActivityError
from planificahoy.models import (
    Activity,
    LocationCandidate,
    RecommendationLevel,
    WeatherSnapshot,
)
from planificahoy.planning_service import PlanningService
from planificahoy.recommendation_service import RecommendationService


class FakeGeocoder:
    def __init__(self) -> None:
        self.received_query: str | None = None

    def search(self, query: str) -> list[LocationCandidate]:
        self.received_query = query
        return [
            LocationCandidate(
                name="San José",
                country="Costa Rica",
                country_code="CR",
                admin_region="San José",
                latitude=9.93333,
                longitude=-84.08333,
                timezone="America/Costa_Rica",
            )
        ]


class FakeWeatherProvider:
    def __init__(self) -> None:
        self.received_arguments: tuple[float, float, str] | None = None
        self.call_count = 0

    def get_weather(
        self, latitude: float, longitude: float, timezone: str
    ) -> WeatherSnapshot:
        self.call_count += 1
        self.received_arguments = (latitude, longitude, timezone)
        return WeatherSnapshot(
            timestamp=datetime(
                2026, 7, 20, 18, tzinfo=ZoneInfo("America/Costa_Rica")
            ),
            temperature_celsius=24.2,
            precipitation_probability_percent=70.0,
            wind_speed_kmh=12.5,
        )


def build_service(
    weather_provider: FakeWeatherProvider | None = None,
) -> PlanningService:
    return PlanningService(
        FakeGeocoder(),
        weather_provider or FakeWeatherProvider(),
        RecommendationService(),
    )


def test_search_locations_normalizes_and_delegates() -> None:
    geocoder = FakeGeocoder()
    service = PlanningService(
        geocoder, FakeWeatherProvider(), RecommendationService()
    )

    result = service.search_locations("  San José  ")

    assert geocoder.received_query == "San José"
    assert result[0].country_code == "CR"


@pytest.mark.parametrize("query", ["", " ", "S"])
def test_search_locations_rejects_short_query(query: str) -> None:
    service = build_service()

    with pytest.raises(InvalidInputError):
        service.search_locations(query)


def test_search_locations_rejects_long_query() -> None:
    service = build_service()

    with pytest.raises(InvalidInputError):
        service.search_locations("S" * 101)


def test_get_weather_delegates_to_provider() -> None:
    weather_provider = FakeWeatherProvider()
    service = build_service(weather_provider)

    snapshot = service.get_weather(
        9.93333, -84.08333, "America/Costa_Rica"
    )

    assert weather_provider.received_arguments == (
        9.93333,
        -84.08333,
        "America/Costa_Rica",
    )
    assert snapshot.wind_speed_kmh == 12.5


def test_get_weather_normalizes_timezone() -> None:
    weather_provider = FakeWeatherProvider()
    service = build_service(weather_provider)

    service.get_weather(9.93333, -84.08333, " America/Costa_Rica ")

    assert weather_provider.received_arguments == (
        9.93333,
        -84.08333,
        "America/Costa_Rica",
    )


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (91, 0),
        (-91, 0),
        (0, 181),
        (0, -181),
        (math.nan, 0),
        (math.inf, 0),
        (-math.inf, 0),
        (0, math.nan),
        (0, math.inf),
        (0, -math.inf),
    ],
)
def test_get_weather_rejects_invalid_coordinates(
    latitude: float, longitude: float
) -> None:
    service = build_service()

    with pytest.raises(InvalidInputError):
        service.get_weather(latitude, longitude, "America/Costa_Rica")


@pytest.mark.parametrize("timezone", ["not/a_timezone", "", "   "])
def test_get_weather_rejects_invalid_timezone(timezone: str) -> None:
    service = build_service()

    with pytest.raises(InvalidInputError) as exc_info:
        service.get_weather(9.93333, -84.08333, timezone)

    assert "America/Costa_Rica" in str(exc_info.value)


def test_get_recommendation_reuses_one_weather_snapshot() -> None:
    weather_provider = FakeWeatherProvider()
    service = build_service(weather_provider)

    result = service.get_recommendation(
        latitude=9.93333,
        longitude=-84.08333,
        timezone="America/Costa_Rica",
        activity=Activity.FOOTBALL,
    )

    assert weather_provider.call_count == 1
    assert result.weather.temperature_celsius == 24.2
    assert result.recommendation.activity is Activity.FOOTBALL
    assert result.recommendation.level is RecommendationLevel.REGULAR


def test_get_recommendation_supports_cycling() -> None:
    service = build_service()

    result = service.get_recommendation(
        latitude=9.93333,
        longitude=-84.08333,
        timezone="America/Costa_Rica",
        activity=Activity.CYCLING,
    )

    assert result.recommendation.activity is Activity.CYCLING
    assert result.recommendation.level is RecommendationLevel.UNFAVORABLE


def test_get_recommendation_rejects_activity_before_weather_call() -> None:
    weather_provider = FakeWeatherProvider()
    service = build_service(weather_provider)

    with pytest.raises(UnsupportedActivityError):
        service.get_recommendation(
            9.93333,
            -84.08333,
            "America/Costa_Rica",
            "skating",
        )

    assert weather_provider.call_count == 0
