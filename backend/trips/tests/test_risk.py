import pytest

from trips.services.risk import Risk, assess, load_level, rain_level, snow_level, wind_level


@pytest.mark.parametrize(
    "mph, expected",
    [
        (0, Risk.LOW),
        (24.9, Risk.LOW),
        (25, Risk.MODERATE),
        (34.9, Risk.MODERATE),
        (35, Risk.HIGH),
        (44.9, Risk.HIGH),
        (45, Risk.SEVERE),
        (54.9, Risk.SEVERE),
        (55, Risk.NO_TRAVEL),
        (80, Risk.NO_TRAVEL),
    ],
)
def test_wind_bands(mph, expected):
    assert wind_level(mph) == expected


@pytest.mark.parametrize(
    "rate, expected",
    [
        (0, Risk.LOW),
        (0.09, Risk.LOW),
        (0.10, Risk.MODERATE),
        (0.24, Risk.MODERATE),
        (0.25, Risk.HIGH),
        (0.49, Risk.HIGH),
        (0.50, Risk.SEVERE),
        (1.00, Risk.SEVERE),
        (1.01, Risk.NO_TRAVEL),
    ],
)
def test_rain_bands(rate, expected):
    assert rain_level(rate) == expected


@pytest.mark.parametrize(
    "rate, expected",
    [
        (0, Risk.LOW),
        (0.49, Risk.LOW),
        (0.5, Risk.MODERATE),
        (0.99, Risk.MODERATE),
        (1.0, Risk.HIGH),
        (1.99, Risk.HIGH),
        (2.0, Risk.SEVERE),
        (3.0, Risk.SEVERE),
        (3.01, Risk.NO_TRAVEL),
    ],
)
def test_snow_bands(rate, expected):
    assert snow_level(rate) == expected


@pytest.mark.parametrize(
    "mph, load, expected",
    [
        (55, 0, Risk.NO_TRAVEL),
        (60, 10_000, Risk.NO_TRAVEL),
        (45, 30_000, Risk.LOW),
        (45, 30_001, Risk.NO_TRAVEL),
        (54.9, 35_000, Risk.NO_TRAVEL),
        (35, 40_000, Risk.LOW),
        (35, 40_001, Risk.SEVERE),
        (44.9, 80_000, Risk.SEVERE),
        (34.9, 80_000, Risk.LOW),
    ],
)
def test_load_rules(mph, load, expected):
    assert load_level(mph, load) == expected


def test_assess_takes_worst_condition():
    result = assess(wind_mph=10, rain_in_hr=0.3, snow_in_hr=1.5, load_lb=20_000)
    assert result.level == Risk.HIGH
    assert result.rain == Risk.HIGH
    assert result.snow == Risk.HIGH


def test_heavy_load_escalates_high_wind_to_severe():
    light = assess(38, 0, 0, 20_000)
    heavy = assess(38, 0, 0, 42_000)
    assert light.level == Risk.HIGH
    assert heavy.level == Risk.SEVERE
    assert any("load" in r for r in heavy.reasons)


def test_heavy_load_escalates_severe_wind_to_no_travel():
    assert assess(48, 0, 0, 30_000).level == Risk.SEVERE
    assert assess(48, 0, 0, 31_000).level == Risk.NO_TRAVEL


def test_calm_weather_has_no_reasons():
    result = assess(5, 0, 0, 80_000)
    assert result.level == Risk.LOW
    assert result.reasons == []
