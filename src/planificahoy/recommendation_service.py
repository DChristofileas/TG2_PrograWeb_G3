"""Deterministic recommendation rules independent of delivery and providers."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import math
from types import MappingProxyType

from planificahoy.errors import (
    InvalidWeatherSnapshotError,
    UnsupportedActivityError,
)
from planificahoy.models import (
    Activity,
    Recommendation,
    RecommendationLevel,
    WeatherSnapshot,
)


@dataclass(frozen=True, slots=True)
class ActivityThresholds:
    """Configurable thresholds used by the common evaluation algorithm."""

    temperature_minimum: float
    temperature_favorable_minimum: float
    temperature_favorable_maximum: float
    temperature_maximum: float
    precipitation_warning_from: float
    precipitation_unfavorable_from: float
    wind_warning_from: float
    wind_unfavorable_from: float

    def __post_init__(self) -> None:
        if not (
            self.temperature_minimum
            < self.temperature_favorable_minimum
            <= self.temperature_favorable_maximum
            < self.temperature_maximum
        ):
            raise ValueError("Los umbrales de temperatura no son coherentes.")
        if not (
            0
            <= self.precipitation_warning_from
            < self.precipitation_unfavorable_from
            <= 100
        ):
            raise ValueError("Los umbrales de precipitación no son coherentes.")
        if not 0 <= self.wind_warning_from < self.wind_unfavorable_from:
            raise ValueError("Los umbrales de viento no son coherentes.")


ACTIVITY_RULES: Mapping[Activity, ActivityThresholds] = MappingProxyType(
    {
        Activity.FOOTBALL: ActivityThresholds(
            temperature_minimum=5,
            temperature_favorable_minimum=12,
            temperature_favorable_maximum=28,
            temperature_maximum=34,
            precipitation_warning_from=40,
            precipitation_unfavorable_from=75,
            wind_warning_from=25,
            wind_unfavorable_from=40,
        ),
        Activity.RUNNING: ActivityThresholds(
            temperature_minimum=0,
            temperature_favorable_minimum=8,
            temperature_favorable_maximum=24,
            temperature_maximum=30,
            precipitation_warning_from=40,
            precipitation_unfavorable_from=75,
            wind_warning_from=25,
            wind_unfavorable_from=40,
        ),
        Activity.PICNIC: ActivityThresholds(
            temperature_minimum=10,
            temperature_favorable_minimum=15,
            temperature_favorable_maximum=28,
            temperature_maximum=32,
            precipitation_warning_from=25,
            precipitation_unfavorable_from=55,
            wind_warning_from=20,
            wind_unfavorable_from=35,
        ),
    }
)


class RecommendationService:
    """Evaluate one WeatherSnapshot using the selected activity's rules."""

    def parse_activity(self, activity: Activity | str) -> Activity:
        if isinstance(activity, Activity):
            return activity
        if not isinstance(activity, str):
            raise UnsupportedActivityError("La actividad seleccionada no es válida.")
        try:
            return Activity(activity.strip().lower())
        except ValueError as exc:
            supported = ", ".join(item.value for item in Activity)
            raise UnsupportedActivityError(
                f"Actividad no soportada. Opciones disponibles: {supported}."
            ) from exc

    def evaluate(
        self, snapshot: WeatherSnapshot, activity: Activity | str
    ) -> Recommendation:
        selected_activity = self.parse_activity(activity)
        _validate_snapshot(snapshot)
        thresholds = ACTIVITY_RULES[selected_activity]

        conditions = (
            self._evaluate_temperature(snapshot.temperature_celsius, thresholds),
            self._evaluate_precipitation(
                snapshot.precipitation_probability_percent, thresholds
            ),
            self._evaluate_wind(snapshot.wind_speed_kmh, thresholds),
        )
        levels = tuple(level for level, _reason in conditions)
        reasons = tuple(
            reason
            for level, reason in conditions
            if level is not RecommendationLevel.FAVORABLE and reason is not None
        )

        if RecommendationLevel.UNFAVORABLE in levels:
            return Recommendation(
                activity=selected_activity,
                level=RecommendationLevel.UNFAVORABLE,
                summary=(
                    "Existe al menos una condición desfavorable para realizar "
                    "esta actividad."
                ),
                reasons=reasons,
            )
        if RecommendationLevel.REGULAR in levels:
            return Recommendation(
                activity=selected_activity,
                level=RecommendationLevel.REGULAR,
                summary=(
                    "Las condiciones son aceptables, pero requieren precaución "
                    "para esta actividad."
                ),
                reasons=reasons,
            )
        return Recommendation(
            activity=selected_activity,
            level=RecommendationLevel.FAVORABLE,
            summary=(
                "Las condiciones están dentro de los rangos favorables "
                "definidos para esta actividad."
            ),
            reasons=(
                "Temperatura, precipitación y viento se encuentran dentro de "
                "los rangos favorables del prototipo.",
            ),
        )

    @staticmethod
    def _evaluate_temperature(
        value: float, thresholds: ActivityThresholds
    ) -> tuple[RecommendationLevel, str | None]:
        if (
            value < thresholds.temperature_minimum
            or value > thresholds.temperature_maximum
        ):
            return (
                RecommendationLevel.UNFAVORABLE,
                "La temperatura de "
                f"{_format_number(value)} °C está fuera del rango orientativo "
                f"de {_format_number(thresholds.temperature_minimum)} a "
                f"{_format_number(thresholds.temperature_maximum)} °C.",
            )
        if (
            thresholds.temperature_favorable_minimum
            <= value
            <= thresholds.temperature_favorable_maximum
        ):
            return RecommendationLevel.FAVORABLE, None
        return (
            RecommendationLevel.REGULAR,
            "La temperatura de "
            f"{_format_number(value)} °C está fuera del rango favorable de "
            f"{_format_number(thresholds.temperature_favorable_minimum)} a "
            f"{_format_number(thresholds.temperature_favorable_maximum)} °C.",
        )

    @staticmethod
    def _evaluate_precipitation(
        value: float, thresholds: ActivityThresholds
    ) -> tuple[RecommendationLevel, str | None]:
        if value >= thresholds.precipitation_unfavorable_from:
            return (
                RecommendationLevel.UNFAVORABLE,
                "La probabilidad de precipitación de "
                f"{_format_number(value)} % se considera desfavorable para "
                "esta actividad.",
            )
        if value >= thresholds.precipitation_warning_from:
            return (
                RecommendationLevel.REGULAR,
                "La probabilidad de precipitación de "
                f"{_format_number(value)} % requiere precaución.",
            )
        return RecommendationLevel.FAVORABLE, None

    @staticmethod
    def _evaluate_wind(
        value: float, thresholds: ActivityThresholds
    ) -> tuple[RecommendationLevel, str | None]:
        if value >= thresholds.wind_unfavorable_from:
            return (
                RecommendationLevel.UNFAVORABLE,
                "La velocidad del viento de "
                f"{_format_number(value)} km/h se considera desfavorable para "
                "esta actividad.",
            )
        if value >= thresholds.wind_warning_from:
            return (
                RecommendationLevel.REGULAR,
                "La velocidad del viento de "
                f"{_format_number(value)} km/h requiere precaución.",
            )
        return RecommendationLevel.FAVORABLE, None


def _validate_snapshot(snapshot: WeatherSnapshot) -> None:
    if not isinstance(snapshot, WeatherSnapshot):
        raise InvalidWeatherSnapshotError(
            "No se recibió una medición meteorológica válida."
        )
    if (
        not isinstance(snapshot.timestamp, datetime)
        or snapshot.timestamp.tzinfo is None
        or snapshot.timestamp.utcoffset() is None
    ):
        raise InvalidWeatherSnapshotError(
            "La medición meteorológica debe incluir fecha, hora y zona horaria."
        )

    temperature = _validated_number(
        snapshot.temperature_celsius, "temperatura"
    )
    precipitation = _validated_number(
        snapshot.precipitation_probability_percent,
        "probabilidad de precipitación",
    )
    wind_speed = _validated_number(snapshot.wind_speed_kmh, "velocidad del viento")

    if not 0 <= precipitation <= 100:
        raise InvalidWeatherSnapshotError(
            "La probabilidad de precipitación debe estar entre 0 y 100."
        )
    if wind_speed < 0:
        raise InvalidWeatherSnapshotError(
            "La velocidad del viento no puede ser negativa."
        )

    # Reading the value documents that every numeric field was validated.
    del temperature


def _validated_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidWeatherSnapshotError(f"El campo {field} no es numérico.")
    number = float(value)
    if not math.isfinite(number):
        raise InvalidWeatherSnapshotError(f"El campo {field} no es finito.")
    return number


def _format_number(value: float) -> str:
    return f"{value:g}"
