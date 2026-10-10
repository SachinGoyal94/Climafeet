from datetime import UTC, datetime, timedelta

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from trips.services import weather
from trips.services.geo import haversine_m
from trips.services.heatmap import HOURS, MAX_CELLS, corridor_cells

from .test_api import make_fake_weather

LINE = [(41.88, -87.63), (41.5, -90.0), (40.8, -96.8), (39.74, -104.98)]


def test_cells_stay_near_the_route():
    cells, step = corridor_cells([LINE])
    assert 0 < len(cells) <= MAX_CELLS
    # route vertices are ~300 km apart, so nothing should be much further than that
    far = max(min(haversine_m(lat, lon, a, b) for a, b in LINE) for lat, lon in cells)
    assert far < 400_000
    assert step >= 0.1


def test_long_routes_coarsen_grid_to_cap_cells():
    long_line = [(25.8, -80.2), (34.0, -118.2)]
    cells, step = corridor_cells([long_line])
    assert len(cells) <= MAX_CELLS
    assert step > 0.3


@pytest.fixture
def client(monkeypatch):
    cache.clear()
    monkeypatch.setattr(weather, "get_json", make_fake_weather(wind=38.0))
    return APIClient()


def test_heatmap_endpoint_shapes(client):
    start = datetime.now(UTC) + timedelta(hours=1)
    body = {
        "lines": [[[lon, lat] for lat, lon in LINE]],
        "start": start.isoformat(),
        "load_lb": 42_000,
    }
    res = client.post("/api/heatmap", body, format="json")
    assert res.status_code == 200, res.data
    data = res.json()
    n = len(data["cells"])
    assert len(data["risk"]) == HOURS + 1
    assert all(len(row) == n for row in data["risk"])
    # 38 mph with a 42k lb load is Severe everywhere
    assert set(data["risk"][0]) == {3}
    assert data["wind_mph"][10][0] == 38.0


def test_heatmap_rejects_bad_coordinates(client):
    body = {"lines": [[[500, 10], [1, 1]]], "start": datetime.now(UTC).isoformat(), "load_lb": 0}
    assert client.post("/api/heatmap", body, format="json").status_code == 400
