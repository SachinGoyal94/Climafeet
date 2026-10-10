from datetime import UTC, date, datetime, timedelta

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from trips.services import tomtom, weather

ORIGIN = {"label": "Chicago, IL", "lat": 41.88, "lon": -87.63}
DEST = {"label": "Detroit, MI", "lat": 42.33, "lon": -83.05}


class FakeResp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


def _line(stops, n=40):
    pts = []
    for (a_lat, a_lon), (b_lat, b_lon) in zip(stops, stops[1:], strict=False):
        for i in range(n):
            t = i / n
            pts.append(
                {"latitude": a_lat + (b_lat - a_lat) * t, "longitude": a_lon + (b_lon - a_lon) * t}
            )
    pts.append({"latitude": stops[-1][0], "longitude": stops[-1][1]})
    return pts


def _route(stops, length_m, secs):
    return {
        "summary": {
            "lengthInMeters": length_m,
            "travelTimeInSeconds": secs,
            "trafficDelayInSeconds": 0,
        },
        "legs": [{"points": _line(stops)}],
        "guidance": {
            "instructions": [{"routeOffsetInMeters": length_m / 2, "travelTimeInSeconds": secs / 2}]
        },
    }


def fake_tomtom(url, params, provider):
    path = url.split("/calculateRoute/")[1].removesuffix("/json")
    stops = [tuple(float(x) for x in s.split(",")) for s in path.split(":")]
    if len(stops) == 2:
        return None, {"routes": [_route(stops, 450_000, 16_000), _route(stops, 470_000, 17_000)]}
    return None, {"routes": [_route(stops, 520_000, 19_000)]}


def make_fake_weather(wind=40.0):
    def fake(url, params, provider):
        start = date.fromisoformat(params["start_date"])
        end = date.fromisoformat(params["end_date"])
        t0 = int(datetime(start.year, start.month, start.day, tzinfo=UTC).timestamp())
        hours = ((end - start).days + 1) * 24
        lats = [float(x) for x in params["latitude"].split(",")]
        blocks = []
        for _ in lats:
            blocks.append(
                {
                    "hourly": {
                        "time": [t0 + h * 3600 for h in range(hours)],
                        "wind_speed_10m": [wind] * hours,
                        "wind_gusts_10m": [wind + 10] * hours,
                        "rain": [0.0] * hours,
                        "showers": [0.0] * hours,
                        "snowfall": [0.0] * hours,
                        "temperature_2m": [50.0] * hours,
                    }
                }
            )
        return FakeResp(200, blocks), blocks

    return fake


@pytest.fixture(autouse=True)
def setup(settings, monkeypatch):
    settings.TOMTOM_API_KEY = "test"
    cache.clear()
    monkeypatch.setattr(tomtom, "get_json", fake_tomtom)
    monkeypatch.setattr(weather, "get_json", make_fake_weather())


def payload(**over):
    body = {
        "origin": ORIGIN,
        "destination": DEST,
        "departure": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
        "load_lb": 20_000,
        "interval_miles": 25,
    }
    body.update(over)
    return body


def post(body):
    return APIClient().post("/api/trips/plan", body, format="json")


def test_plan_returns_three_routes_with_checkpoints():
    res = post(payload())
    assert res.status_code == 200, res.data
    data = res.json()
    assert [r["id"] for r in data["routes"]] == ["A", "B", "C"]
    for r in data["routes"]:
        cps = r["checkpoints"]
        assert cps[0]["mile"] == 0
        assert cps[-1]["mile"] == pytest.approx(r["distance_miles"], abs=0.1)
        assert sum(c["segment_miles"] for c in cps) == pytest.approx(r["distance_miles"], abs=0.5)
        assert cps[-1]["eta"] > cps[0]["eta"]


def test_uniform_weather_picks_fastest_route():
    data = post(payload()).json()
    assert data["recommendation"]["best_id"] == "A"
    assert all(r["summary"]["max_label"] == "High" for r in data["routes"])


def test_heavy_load_turns_high_wind_severe():
    data = post(payload(load_lb=45_000)).json()
    assert all(r["summary"]["max_label"] == "Severe" for r in data["routes"])
    assert data["recommendation"]["warning"]


def _off_direct_line(lat, lon):
    t = (lon - ORIGIN["lon"]) / (DEST["lon"] - ORIGIN["lon"])
    line_lat = ORIGIN["lat"] + (DEST["lat"] - ORIGIN["lat"]) * t
    return abs(lat - line_lat) > 0.2


def test_slower_detour_wins_when_it_avoids_wind(monkeypatch):
    windy = make_fake_weather(wind=40.0)

    def calm_off_line(url, params, provider):
        resp, blocks = windy(url, params, provider)
        lats = [float(x) for x in params["latitude"].split(",")]
        lons = [float(x) for x in params["longitude"].split(",")]
        for lat, lon, b in zip(lats, lons, blocks, strict=True):
            if _off_direct_line(lat, lon):
                b["hourly"]["wind_speed_10m"] = [5.0] * len(b["hourly"]["time"])
        return resp, blocks

    monkeypatch.setattr(weather, "get_json", calm_off_line)
    data = post(payload()).json()
    by_id = {r["id"]: r for r in data["routes"]}
    assert data["recommendation"]["best_id"] == "C"
    assert by_id["C"]["duration_s"] > by_id["A"]["duration_s"]
    assert by_id["C"]["summary"]["miles"]["High"] < by_id["A"]["summary"]["miles"]["High"]
    assert "High miles" in data["recommendation"]["reason"]


@pytest.mark.parametrize(
    "over",
    [
        {"interval_miles": 15},
        {"load_lb": -5},
        {"departure": "2020-01-01T00:00:00Z"},
        {"origin": {"label": ""}},
    ],
)
def test_validation_errors(over):
    assert post(payload(**over)).status_code == 400


def test_routing_error_is_reported(monkeypatch):
    def failing(url, params, provider):
        return FakeResp(400, {"detailedError": {"message": "Unreachable destination"}}), None

    monkeypatch.setattr(tomtom, "get_json", failing)
    res = post(payload())
    assert res.status_code == 422
    assert "Unreachable" in res.json()["detail"]


def test_geocode_short_query_returns_empty():
    res = APIClient().get("/api/geocode", {"q": "ch"})
    assert res.json() == {"results": []}
