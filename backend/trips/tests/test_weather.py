import pytest

from trips.services.weather import Series, _parse, snap

T0 = 1_791_590_400


def make_series():
    return Series(
        times=[T0, T0 + 3600, T0 + 7200],
        wind=[10.0, 20.0, 30.0],
        gust=[15.0, 25.0, 35.0],
        rain=[0.0, 0.2, 0.6],
        snow=[0.0, 0.0, 1.0],
        temp=[40.0, 42.0, 44.0],
    )


def test_wind_is_interpolated_between_hours():
    s = make_series().at(T0 + 1800)
    assert s.wind_mph == pytest.approx(15)
    assert s.temp_f == pytest.approx(41)


def test_precip_uses_hour_ending_after_eta():
    s = make_series()
    assert s.at(T0 + 1800).rain_in_hr == 0.2
    assert s.at(T0 + 3600).rain_in_hr == 0.2
    assert s.at(T0 + 3601).rain_in_hr == 0.6


def test_times_outside_range_clamp():
    s = make_series()
    assert s.at(T0 - 999).wind_mph == 10
    assert s.at(T0 + 99_999).wind_mph == 30


def test_parse_sums_rain_and_showers_and_handles_nulls():
    block = {
        "hourly": {
            "time": [T0, T0 + 3600],
            "wind_speed_10m": [5, None],
            "wind_gusts_10m": [9, 10],
            "rain": [0.1, None],
            "showers": [0.05, 0.2],
            "snowfall": [0, 0],
            "temperature_2m": [50, 51],
        }
    }
    s = _parse(block)
    assert s.rain == pytest.approx([0.15, 0.2])
    assert s.wind == [5.0, 0.0]


def test_snap_groups_nearby_points():
    assert snap(41.881, -87.629) == snap(41.889, -87.641)
    assert snap(41.881, -87.629) != snap(41.95, -87.629)
