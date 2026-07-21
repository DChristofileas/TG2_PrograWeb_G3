from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from planificahoy.api.routes import create_router, register_exception_handlers
from planificahoy.errors import (
    ExternalResponseError,
    ExternalServiceConnectionError,
    ExternalServiceTimeoutError,
)
from planificahoy.models import LocationCandidate, WeatherSnapshot
from planificahoy.planning_service import PlanningService
from planificahoy.recommendation_service import RecommendationService


class FakeGeocoder:
    def search(self, _query: str) -> list[LocationCandidate]:
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
    def get_weather(
        self, latitude: float, longitude: float, timezone: str
    ) -> WeatherSnapshot:
        del latitude, longitude, timezone
        return WeatherSnapshot(
            timestamp=datetime(
                2026, 7, 20, 18, tzinfo=ZoneInfo("America/Costa_Rica")
            ),
            temperature_celsius=24.2,
            precipitation_probability_percent=70,
            wind_speed_kmh=12.5,
        )


def build_test_client() -> TestClient:
    app = FastAPI()
    service = PlanningService(
        FakeGeocoder(), FakeWeatherProvider(), RecommendationService()
    )
    register_exception_handlers(app)
    app.include_router(create_router(service))
    return TestClient(app)


def test_health_endpoint() -> None:
    with build_test_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_locations_endpoint_returns_internal_model() -> None:
    with build_test_client() as client:
        response = client.get("/locations", params={"query": "San José"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "San José",
            "country": "Costa Rica",
            "country_code": "CR",
            "admin_region": "San José",
            "latitude": 9.93333,
            "longitude": -84.08333,
            "timezone": "America/Costa_Rica",
        }
    ]


def test_weather_endpoint_returns_internal_model() -> None:
    with build_test_client() as client:
        response = client.get(
            "/weather",
            params={
                "latitude": 9.93333,
                "longitude": -84.08333,
                "timezone": "America/Costa_Rica",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "timestamp": "2026-07-20T18:00:00-06:00",
        "temperature_celsius": 24.2,
        "precipitation_probability_percent": 70.0,
        "wind_speed_kmh": 12.5,
    }


def test_weather_endpoint_rejects_invalid_coordinates() -> None:
    with build_test_client() as client:
        response = client.get(
            "/weather",
            params={
                "latitude": 91,
                "longitude": -84.08333,
                "timezone": "America/Costa_Rica",
            },
        )

    assert response.status_code == 422


def test_locations_endpoint_rejects_short_query() -> None:
    with build_test_client() as client:
        response = client.get("/locations", params={"query": "S"})

    assert response.status_code == 422


def test_recommendation_endpoint_returns_weather_and_recommendation() -> None:
    with build_test_client() as client:
        response = client.get(
            "/recommendation",
            params={
                "latitude": 9.93333,
                "longitude": -84.08333,
                "timezone": "America/Costa_Rica",
                "activity": "football",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["weather"] == {
        "timestamp": "2026-07-20T18:00:00-06:00",
        "temperature_celsius": 24.2,
        "precipitation_probability_percent": 70.0,
        "wind_speed_kmh": 12.5,
    }
    assert payload["recommendation"] == {
        "activity": "football",
        "level": "REGULAR",
        "summary": (
            "Las condiciones son aceptables, pero requieren precaución para "
            "esta actividad."
        ),
        "reasons": [
            "La probabilidad de precipitación de 70 % requiere precaución."
        ],
    }


@pytest.mark.parametrize("activity", ["", "cycling"])
def test_recommendation_endpoint_rejects_invalid_activity(activity: str) -> None:
    with build_test_client() as client:
        response = client.get(
            "/recommendation",
            params={
                "latitude": 9.93333,
                "longitude": -84.08333,
                "timezone": "America/Costa_Rica",
                "activity": activity,
            },
        )

    assert response.status_code == 422


def test_recommendation_endpoint_preserves_provider_error_handling() -> None:
    class FailingWeatherProvider:
        def get_weather(
            self, latitude: float, longitude: float, timezone: str
        ) -> WeatherSnapshot:
            del latitude, longitude, timezone
            raise ExternalServiceConnectionError("Proveedor no disponible.")

    app = FastAPI()
    service = PlanningService(
        FakeGeocoder(), FailingWeatherProvider(), RecommendationService()
    )
    register_exception_handlers(app)
    app.include_router(create_router(service))

    with TestClient(app) as client:
        response = client.get(
            "/recommendation",
            params={
                "latitude": 9.93333,
                "longitude": -84.08333,
                "timezone": "America/Costa_Rica",
                "activity": "football",
            },
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Proveedor no disponible."}


def test_recommendation_endpoint_hides_invalid_snapshot_details() -> None:
    class InvalidWeatherProvider:
        def get_weather(
            self, latitude: float, longitude: float, timezone: str
        ) -> WeatherSnapshot:
            del latitude, longitude, timezone
            return WeatherSnapshot(
                timestamp=datetime(
                    2026, 7, 20, 18, tzinfo=ZoneInfo("America/Costa_Rica")
                ),
                temperature_celsius=20,
                precipitation_probability_percent=101,
                wind_speed_kmh=10,
            )

    app = FastAPI()
    service = PlanningService(
        FakeGeocoder(), InvalidWeatherProvider(), RecommendationService()
    )
    register_exception_handlers(app)
    app.include_router(create_router(service))

    with TestClient(app) as client:
        response = client.get(
            "/recommendation",
            params={
                "latitude": 9.93333,
                "longitude": -84.08333,
                "timezone": "America/Costa_Rica",
                "activity": "football",
            },
        )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "No fue posible evaluar los datos meteorológicos."
    }


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (ExternalServiceTimeoutError("Tiempo de espera agotado."), 504),
        (ExternalServiceConnectionError("Proveedor no disponible."), 503),
        (ExternalResponseError("Respuesta externa invalida."), 502),
    ],
)
def test_routes_translate_external_errors_without_tracebacks(
    error: Exception, expected_status: int
) -> None:
    class FailingGeocoder:
        def search(self, _query: str) -> list[LocationCandidate]:
            raise error

    app = FastAPI()
    service = PlanningService(
        FailingGeocoder(), FakeWeatherProvider(), RecommendationService()
    )
    register_exception_handlers(app)
    app.include_router(create_router(service))

    with TestClient(app) as client:
        response = client.get("/locations", params={"query": "San José"})

    assert response.status_code == expected_status
    assert response.json() == {"detail": str(error)}
