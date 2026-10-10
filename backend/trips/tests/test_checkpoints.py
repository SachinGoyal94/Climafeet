from datetime import UTC, datetime, timedelta

import pytest

from trips.services.checkpoints import build_checkpoints, sample_miles
from trips.services.geo import (
    METERS_PER_MILE,
    cumulative_distances,
    haversine_m,
    offset_point,
    point_at,
    simplify,
)


def test_haversine_one_degree_latitude():
    assert haversine_m(0, 0, 1, 0) == pytest.approx(111_195, rel=1e-3)


def test_point_at_midpoint():
    pts = [(0.0, 0.0), (0.0, 1.0)]
    cum = cumulative_distances(pts)
    lat, lon = point_at(pts, cum, cum[-1] / 2)
    assert lat == pytest.approx(0)
    assert lon == pytest.approx(0.5)


def test_offset_point_round_trip_distance():
    lat, lon = offset_point(40, -100, 90, 20_000)
    assert haversine_m(40, -100, lat, lon) == pytest.approx(20_000, rel=1e-3)


def test_simplify_drops_collinear_points():
    pts = [(0.0, i / 100) for i in range(101)]
    assert simplify(pts) == [pts[0], pts[-1]]


def test_simplify_keeps_corners():
    pts = [(0.0, 0.0), (0.0, 0.5), (0.0, 1.0), (0.5, 1.0), (1.0, 1.0)]
    out = simplify(pts)
    assert (0.0, 1.0) in out
    assert len(out) == 3


def test_sample_miles_includes_start_and_destination():
    assert sample_miles(42, 10) == [0, 10, 20, 30, 40, 42]
    assert sample_miles(50, 25) == [0, 25, 50]


def _straight_route(miles):
    # due east along the equator, 1 degree is about 69.1 miles
    deg = miles / 69.093
    return [(0.0, deg * i / 100) for i in range(101)]


def test_checkpoint_segments_sum_to_route_length():
    pts = _straight_route(105)
    length_m = 105 * METERS_PER_MILE
    dep = datetime(2026, 10, 10, 12, tzinfo=UTC)
    cps = build_checkpoints(pts, length_m, 7200, [], dep, 25)
    assert [round(c.mile) for c in cps] == [0, 25, 50, 75, 100, 105]
    assert sum(c.segment_miles for c in cps) == pytest.approx(105)


def test_checkpoint_eta_follows_uneven_timing():
    pts = _straight_route(100)
    length_m = 100 * METERS_PER_MILE
    dep = datetime(2026, 10, 10, 12, tzinfo=UTC)
    # first half is slow (1.5h), second half fast (0.5h)
    timing = [(50 * METERS_PER_MILE, 5400)]
    cps = build_checkpoints(pts, length_m, 7200, timing, dep, 50)
    assert cps[0].eta == dep
    assert cps[1].eta == dep + timedelta(hours=1.5)
    assert cps[2].eta == dep + timedelta(hours=2)


def test_checkpoints_ignore_bad_timing_rows():
    pts = _straight_route(20)
    dep = datetime(2026, 10, 10, tzinfo=UTC)
    timing = [(5000, 300), (5000, 310), (4000, 900)]
    cps = build_checkpoints(pts, 20 * METERS_PER_MILE, 1200, timing, dep, 10)
    etas = [c.eta for c in cps]
    assert etas == sorted(etas)
