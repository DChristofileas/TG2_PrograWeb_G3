"""HTTP routes and translation of application errors."""

from typing import Annotated

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from planificahoy.errors import (
    ExternalResponseError,
    ExternalServiceConnectionError,
    ExternalServiceError,
    ExternalServiceRateLimitError,
    ExternalServiceRequestError,
    ExternalServiceTimeoutError,
    ExternalServiceUnavailableError,
    InvalidInputError,
    InvalidWeatherSnapshotError,
)
from planificahoy.models import (
    Activity,
    LocationCandidate,
    RecommendationResult,
    WeatherSnapshot,
)
from planificahoy.planning_service import PlanningService


def create_router(planning_service: PlanningService) -> APIRouter:
    router = APIRouter()

    @router.get("/health", response_model=dict[str, str])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/locations", response_model=list[LocationCandidate])
    def locations(
        query: Annotated[str, Query(min_length=2, max_length=100)],
    ) -> list[LocationCandidate]:
        return planning_service.search_locations(query)

    @router.get("/weather", response_model=WeatherSnapshot)
    def weather(
        latitude: Annotated[float, Query(ge=-90, le=90)],
        longitude: Annotated[float, Query(ge=-180, le=180)],
        timezone: Annotated[str, Query(min_length=1, max_length=100)],
    ) -> WeatherSnapshot:
        return planning_service.get_weather(latitude, longitude, timezone)

    @router.get("/recommendation", response_model=RecommendationResult)
    def recommendation(
        latitude: Annotated[float, Query(ge=-90, le=90)],
        longitude: Annotated[float, Query(ge=-180, le=180)],
        timezone: Annotated[str, Query(min_length=1, max_length=100)],
        activity: Annotated[Activity, Query()],
    ) -> RecommendationResult:
        return planning_service.get_recommendation(
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            activity=activity,
        )

    return router


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidInputError)
    async def invalid_input_handler(
        _request: Request, exc: InvalidInputError
    ) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(InvalidWeatherSnapshotError)
    async def invalid_snapshot_handler(
        _request: Request, _exc: InvalidWeatherSnapshotError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "No fue posible evaluar los datos meteorológicos."
            },
        )

    @app.exception_handler(ExternalServiceTimeoutError)
    async def timeout_handler(
        _request: Request, exc: ExternalServiceTimeoutError
    ) -> JSONResponse:
        return JSONResponse(status_code=504, content={"detail": str(exc)})

    @app.exception_handler(ExternalServiceConnectionError)
    @app.exception_handler(ExternalServiceRateLimitError)
    @app.exception_handler(ExternalServiceUnavailableError)
    async def unavailable_handler(
        _request: Request, exc: ExternalServiceError
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(ExternalServiceRequestError)
    @app.exception_handler(ExternalResponseError)
    @app.exception_handler(ExternalServiceError)
    async def bad_gateway_handler(
        _request: Request, exc: ExternalServiceError
    ) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})
