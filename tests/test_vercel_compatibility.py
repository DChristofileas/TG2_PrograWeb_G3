"""Local checks for the Vercel entrypoint and same-origin frontend."""

from collections.abc import Iterator
import importlib
from pathlib import Path
import tomllib

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_vercel_app() -> FastAPI:
    configuration = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    entrypoint = configuration["tool"]["vercel"]["entrypoint"]
    module_name, separator, attribute_name = entrypoint.partition(":")
    assert separator == ":"

    module = importlib.import_module(module_name)
    application = getattr(module, attribute_name)
    assert isinstance(application, FastAPI)
    return application


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(load_vercel_app()) as test_client:
        yield test_client


def test_vercel_entrypoint_resolves_fastapi_application() -> None:
    assert load_vercel_app().title == "PlanificaHoy API"


def test_root_serves_frontend_index(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>PlanificaHoy" in response.text


def test_css_static_asset_is_available(client: TestClient) -> None:
    response = client.get("/css/styles.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert ":root {" in response.text


def test_javascript_static_asset_is_available(client: TestClient) -> None:
    response = client.get("/js/app.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert 'fetch(`/locations?' in response.text


def test_health_remains_available_from_vercel_app(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "path", ["/", "/css/styles.css", "/js/app.js", "/docs", "/openapi.json"]
)
def test_security_headers_are_sent_without_breaking_public_resources(
    client: TestClient, path: str
) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == (
        "camera=(), geolocation=(), microphone=()"
    )


def test_not_found_response_does_not_expose_internal_details(client: TestClient) -> None:
    response = client.get("/route-that-does-not-exist")

    assert response.status_code == 404
    assert "traceback" not in response.text.lower()
    assert "src\\" not in response.text.lower()


def test_validation_error_keeps_security_headers(client: TestClient) -> None:
    response = client.get("/locations", params={"query": "x"})

    assert response.status_code == 422
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
