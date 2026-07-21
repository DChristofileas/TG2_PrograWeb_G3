import httpx
import pytest

from planificahoy.adapters.open_meteo import (
    OpenMeteoGeocoder,
    OpenMeteoWeatherProvider,
)
from planificahoy.config import Settings
from planificahoy.errors import (
    ExternalResponseError,
    ExternalServiceConnectionError,
    ExternalServiceRateLimitError,
    ExternalServiceRequestError,
    ExternalServiceTimeoutError,
    ExternalServiceUnavailableError,
)


def test_geocoder_translates_multiple_candidates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/search"
        assert request.url.params["name"] == "San Jose"
        assert request.url.params["count"] == "5"
        assert request.url.params["language"] == "es"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "name": "San José",
                        "country": "Costa Rica",
                        "country_code": "CR",
                        "admin1": "San José",
                        "latitude": 9.93333,
                        "longitude": -84.08333,
                        "timezone": "America/Costa_Rica",
                    },
                    {
                        "name": "San José",
                        "country": "Estados Unidos",
                        "country_code": "US",
                        "admin1": "California",
                        "latitude": 37.33939,
                        "longitude": -121.89496,
                        "timezone": "America/Los_Angeles",
                    },
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        candidates = OpenMeteoGeocoder(client, Settings()).search("San Jose")

    assert len(candidates) == 2
    assert candidates[0].country_code == "CR"
    assert candidates[0].admin_region == "San José"
    assert candidates[1].country_code == "US"


def test_geocoder_returns_empty_list_when_location_does_not_exist() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={}))

    with httpx.Client(transport=transport) as client:
        candidates = OpenMeteoGeocoder(client, Settings()).search(
            "ubicacion que no existe"
        )

    assert candidates == []


def test_weather_provider_translates_first_complete_hour() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/forecast"
        assert request.url.params["latitude"] == "9.93333"
        assert request.url.params["longitude"] == "-84.08333"
        assert request.url.params["timezone"] == "America/Costa_Rica"
        assert request.url.params["temperature_unit"] == "celsius"
        assert request.url.params["wind_speed_unit"] == "kmh"
        assert request.url.params["hourly"] == (
            "temperature_2m,precipitation_probability,wind_speed_10m"
        )
        return httpx.Response(
            200,
            json={
                "timezone": "America/Costa_Rica",
                "hourly_units": {
                    "time": "iso8601",
                    "temperature_2m": "°C",
                    "precipitation_probability": "%",
                    "wind_speed_10m": "km/h",
                },
                "hourly": {
                    "time": ["2026-07-20T18:00", "2026-07-20T19:00"],
                    "temperature_2m": [24.2, 23.8],
                    "precipitation_probability": [70, 65],
                    "wind_speed_10m": [12.5, 10.8],
                },
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        snapshot = OpenMeteoWeatherProvider(client, Settings()).get_weather(
            latitude=9.93333,
            longitude=-84.08333,
            timezone="America/Costa_Rica",
        )

    assert snapshot.timestamp.isoformat() == "2026-07-20T18:00:00-06:00"
    assert snapshot.temperature_celsius == 24.2
    assert snapshot.precipitation_probability_percent == 70.0
    assert snapshot.wind_speed_kmh == 12.5


def test_weather_provider_rejects_missing_field() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            json={
                "timezone": "America/Costa_Rica",
                "hourly_units": {
                    "temperature_2m": "°C",
                    "precipitation_probability": "%",
                    "wind_speed_10m": "km/h",
                },
                "hourly": {
                    "time": ["2026-07-20T18:00"],
                    "temperature_2m": [24.2],
                    "precipitation_probability": [70],
                },
            },
        )
    )

    with httpx.Client(transport=transport) as client:
        provider = OpenMeteoWeatherProvider(client, Settings())
        with pytest.raises(ExternalResponseError):
            provider.get_weather(9.93333, -84.08333, "America/Costa_Rica")


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (400, ExternalServiceRequestError),
        (429, ExternalServiceRateLimitError),
        (503, ExternalServiceUnavailableError),
    ],
)
def test_adapter_translates_http_errors(
    status_code: int, expected_error: type[Exception]
) -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(status_code, json={"error": True})
    )

    with httpx.Client(transport=transport) as client:
        geocoder = OpenMeteoGeocoder(client, Settings())
        with pytest.raises(expected_error):
            geocoder.search("San Jose")


def test_adapter_rejects_non_json_response() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, text="not-json")
    )

    with httpx.Client(transport=transport) as client:
        with pytest.raises(ExternalResponseError):
            OpenMeteoGeocoder(client, Settings()).search("San Jose")


def test_adapter_translates_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ExternalServiceTimeoutError):
            OpenMeteoGeocoder(client, Settings()).search("San Jose")


def test_adapter_translates_connection_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ExternalServiceConnectionError):
            OpenMeteoGeocoder(client, Settings()).search("San Jose")

