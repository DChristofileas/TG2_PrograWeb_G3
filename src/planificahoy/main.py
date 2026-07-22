"""FastAPI application composition root."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import httpx

from planificahoy.adapters.open_meteo import (
    OpenMeteoGeocoder,
    OpenMeteoWeatherProvider,
)
from planificahoy.api.routes import create_router, register_exception_handlers
from planificahoy.config import Settings
from planificahoy.planning_service import PlanningService
from planificahoy.recommendation_service import RecommendationService


def create_app(
    settings: Settings | None = None,
    http_client: httpx.Client | None = None,
) -> FastAPI:
    current_settings = settings or Settings.from_env()
    current_settings.validate()

    owns_client = http_client is None
    client = http_client or httpx.Client(
        timeout=current_settings.http_timeout_seconds,
        follow_redirects=False,
    )

    geocoder = OpenMeteoGeocoder(client, current_settings)
    weather_provider = OpenMeteoWeatherProvider(client, current_settings)
    recommendation_service = RecommendationService()
    planning_service = PlanningService(
        geocoder, weather_provider, recommendation_service
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        if owns_client:
            client.close()

    application = FastAPI(
        title="PlanificaHoy API",
        version="0.2.0",
        description=(
            "Backend del MVP para consultar ubicaciones, clima y recomendaciones."
        ),
        lifespan=lifespan,
    )
    register_exception_handlers(application)
    application.include_router(create_router(planning_service))
    _mount_frontend(application)
    return application


def _mount_frontend(application: FastAPI) -> None:
    """Serve the static frontend (HTML/CSS/JS) from the same FastAPI app.

    Kept additive: API routes are registered first, so /locations,
    /recommendation, /weather and /health keep priority. Only the site's
    static assets and the index page are added here.
    """

    frontend_dir = Path(__file__).parent / "frontend"
    if not frontend_dir.is_dir():
        return

    application.mount(
        "/css", StaticFiles(directory=frontend_dir / "css"), name="css"
    )
    application.mount(
        "/js", StaticFiles(directory=frontend_dir / "js"), name="js"
    )

    @application.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(frontend_dir / "index.html")


app = create_app()
