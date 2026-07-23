from dataclasses import replace
from datetime import datetime
import math
from zoneinfo import ZoneInfo

import pytest

from planificahoy.errors import (
    InvalidWeatherSnapshotError,
    UnsupportedActivityError,
)
from planificahoy.models import Activity, RecommendationLevel, WeatherSnapshot
from planificahoy.recommendation_service import (
    ACTIVITY_RULES,
    RecommendationService,
)


REFERENCE_TIME = datetime(
    2026, 7, 20, 18, tzinfo=ZoneInfo("America/Costa_Rica")
)


def make_snapshot(
    temperature: float, precipitation: float, wind_speed: float
) -> WeatherSnapshot:
    return WeatherSnapshot(
        timestamp=REFERENCE_TIME,
        temperature_celsius=temperature,
        precipitation_probability_percent=precipitation,
        wind_speed_kmh=wind_speed,
    )


@pytest.mark.parametrize(
    ("activity", "temperature", "precipitation", "wind_speed"),
    [
        (Activity.FOOTBALL, 20, 20, 10),
        (Activity.RUNNING, 16, 20, 10),
        (Activity.PICNIC, 22, 10, 10),
        (Activity.CYCLING, 18, 20, 10),
    ],
)
def test_each_activity_can_be_favorable(
    activity: Activity,
    temperature: float,
    precipitation: float,
    wind_speed: float,
) -> None:
    result = RecommendationService().evaluate(
        make_snapshot(temperature, precipitation, wind_speed), activity
    )

    assert result.activity is activity
    assert result.level is RecommendationLevel.FAVORABLE
    assert result.reasons


@pytest.mark.parametrize("activity", list(Activity))
def test_each_activity_can_be_regular(activity: Activity) -> None:
    rules = ACTIVITY_RULES[activity]
    snapshot = make_snapshot(
        rules.temperature_favorable_minimum,
        rules.precipitation_warning_from,
        0,
    )

    result = RecommendationService().evaluate(snapshot, activity)

    assert result.level is RecommendationLevel.REGULAR
    assert len(result.reasons) == 1


@pytest.mark.parametrize("activity", list(Activity))
def test_each_activity_can_be_unfavorable(activity: Activity) -> None:
    rules = ACTIVITY_RULES[activity]
    snapshot = make_snapshot(
        rules.temperature_favorable_minimum,
        rules.precipitation_unfavorable_from,
        0,
    )

    result = RecommendationService().evaluate(snapshot, activity)

    assert result.level is RecommendationLevel.UNFAVORABLE
    assert len(result.reasons) == 1


@pytest.mark.parametrize("activity", list(Activity))
def test_favorable_temperature_limits_are_inclusive(activity: Activity) -> None:
    service = RecommendationService()
    rules = ACTIVITY_RULES[activity]

    minimum_result = service.evaluate(
        make_snapshot(rules.temperature_favorable_minimum, 0, 0), activity
    )
    maximum_result = service.evaluate(
        make_snapshot(rules.temperature_favorable_maximum, 0, 0), activity
    )

    assert minimum_result.level is RecommendationLevel.FAVORABLE
    assert maximum_result.level is RecommendationLevel.FAVORABLE


@pytest.mark.parametrize("activity", list(Activity))
def test_outer_temperature_limits_are_regular(activity: Activity) -> None:
    service = RecommendationService()
    rules = ACTIVITY_RULES[activity]

    minimum_result = service.evaluate(
        make_snapshot(rules.temperature_minimum, 0, 0), activity
    )
    maximum_result = service.evaluate(
        make_snapshot(rules.temperature_maximum, 0, 0), activity
    )

    assert minimum_result.level is RecommendationLevel.REGULAR
    assert maximum_result.level is RecommendationLevel.REGULAR


@pytest.mark.parametrize("activity", list(Activity))
def test_temperature_outside_outer_limits_is_unfavorable(
    activity: Activity,
) -> None:
    service = RecommendationService()
    rules = ACTIVITY_RULES[activity]

    below_result = service.evaluate(
        make_snapshot(rules.temperature_minimum - 0.01, 0, 0), activity
    )
    above_result = service.evaluate(
        make_snapshot(rules.temperature_maximum + 0.01, 0, 0), activity
    )

    assert below_result.level is RecommendationLevel.UNFAVORABLE
    assert above_result.level is RecommendationLevel.UNFAVORABLE


@pytest.mark.parametrize("activity", list(Activity))
def test_exact_precipitation_limits(activity: Activity) -> None:
    service = RecommendationService()
    rules = ACTIVITY_RULES[activity]
    temperature = rules.temperature_favorable_minimum

    below_warning = service.evaluate(
        make_snapshot(temperature, rules.precipitation_warning_from - 0.01, 0),
        activity,
    )
    warning = service.evaluate(
        make_snapshot(temperature, rules.precipitation_warning_from, 0),
        activity,
    )
    unfavorable = service.evaluate(
        make_snapshot(temperature, rules.precipitation_unfavorable_from, 0),
        activity,
    )

    assert below_warning.level is RecommendationLevel.FAVORABLE
    assert warning.level is RecommendationLevel.REGULAR
    assert unfavorable.level is RecommendationLevel.UNFAVORABLE


@pytest.mark.parametrize("activity", list(Activity))
def test_exact_wind_limits(activity: Activity) -> None:
    service = RecommendationService()
    rules = ACTIVITY_RULES[activity]
    temperature = rules.temperature_favorable_minimum

    below_warning = service.evaluate(
        make_snapshot(temperature, 0, rules.wind_warning_from - 0.01), activity
    )
    warning = service.evaluate(
        make_snapshot(temperature, 0, rules.wind_warning_from), activity
    )
    unfavorable = service.evaluate(
        make_snapshot(temperature, 0, rules.wind_unfavorable_from), activity
    )

    assert below_warning.level is RecommendationLevel.FAVORABLE
    assert warning.level is RecommendationLevel.REGULAR
    assert unfavorable.level is RecommendationLevel.UNFAVORABLE


def test_any_unfavorable_condition_dominates_warnings() -> None:
    result = RecommendationService().evaluate(
        make_snapshot(10, 60, 40), Activity.FOOTBALL
    )

    assert result.level is RecommendationLevel.UNFAVORABLE
    assert len(result.reasons) == 3


def test_activity_parser_accepts_case_and_extra_spaces() -> None:
    result = RecommendationService().evaluate(
        make_snapshot(18, 20, 10), " CYCLING "
    )

    assert result.activity is Activity.CYCLING
    assert result.level is RecommendationLevel.FAVORABLE


def test_unknown_activity_is_rejected() -> None:
    with pytest.raises(UnsupportedActivityError):
        RecommendationService().evaluate(
            make_snapshot(20, 0, 0), "skating"
        )


def test_empty_activity_is_rejected() -> None:
    with pytest.raises(UnsupportedActivityError):
        RecommendationService().evaluate(make_snapshot(20, 0, 0), "  ")


@pytest.mark.parametrize(
    "snapshot",
    [
        make_snapshot(math.nan, 0, 0),
        make_snapshot(20, -0.1, 0),
        make_snapshot(20, 100.1, 0),
        make_snapshot(20, 0, -0.1),
        replace(make_snapshot(20, 0, 0), timestamp=datetime(2026, 7, 20, 18)),
    ],
)
def test_invalid_weather_snapshot_is_rejected(
    snapshot: WeatherSnapshot,
) -> None:
    with pytest.raises(InvalidWeatherSnapshotError):
        RecommendationService().evaluate(snapshot, Activity.FOOTBALL)


def test_extreme_but_valid_values_are_evaluated() -> None:
    result = RecommendationService().evaluate(
        make_snapshot(-80, 100, 300), Activity.RUNNING
    )

    assert result.level is RecommendationLevel.UNFAVORABLE
    assert len(result.reasons) == 3
