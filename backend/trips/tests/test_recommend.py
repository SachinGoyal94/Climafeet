import pytest

from trips.services.recommend import Candidate, recommend, summarize
from trips.services.risk import Risk


def route(id_, segments, hours):
    return Candidate(id=id_, name=f"Route {id_}", duration_s=hours * 3600, risk=summarize(segments))


def test_summarize_counts_miles_and_weighted_average():
    s = summarize([(10, Risk.LOW), (10, Risk.HIGH), (20, Risk.SEVERE)])
    assert s.miles[Risk.HIGH] == 10
    assert s.miles[Risk.SEVERE] == 20
    assert s.total_miles == 40
    assert s.avg_risk == pytest.approx((0 + 20 + 60) / 40)
    assert s.max_level == Risk.SEVERE


def test_summarize_empty_route():
    s = summarize([])
    assert s.total_miles == 0
    assert s.avg_risk == 0
    assert s.max_level == Risk.LOW


def test_fewest_severe_miles_beats_faster_route():
    a = route("A", [(50, Risk.LOW), (10, Risk.SEVERE)], hours=2)
    b = route("B", [(70, Risk.HIGH)], hours=5)
    rec = recommend([a, b])
    assert rec.best_id == "B"
    assert "Severe" in rec.reason


def test_high_miles_break_severe_tie():
    a = route("A", [(30, Risk.HIGH), (30, Risk.LOW)], hours=1)
    b = route("B", [(10, Risk.HIGH), (50, Risk.MODERATE)], hours=2)
    assert recommend([a, b]).best_id == "B"


def test_average_risk_breaks_high_tie():
    a = route("A", [(60, Risk.MODERATE)], hours=1)
    b = route("B", [(30, Risk.MODERATE), (30, Risk.LOW)], hours=2)
    rec = recommend([a, b])
    assert rec.best_id == "B"
    assert "average risk" in rec.reason


def test_travel_time_is_last_tiebreaker():
    a = route("A", [(60, Risk.LOW)], hours=3)
    b = route("B", [(60, Risk.LOW)], hours=2.5)
    rec = recommend([a, b])
    assert rec.best_id == "B"
    assert "30 min faster" in rec.reason


def test_no_travel_miles_rank_worse_than_severe():
    a = route("A", [(5, Risk.NO_TRAVEL), (55, Risk.LOW)], hours=1)
    b = route("B", [(40, Risk.SEVERE), (20, Risk.LOW)], hours=2)
    rec = recommend([a, b])
    assert rec.best_id == "B"
    assert rec.warning and "Severe" in rec.warning


def test_warning_when_every_route_has_no_travel():
    a = route("A", [(5, Risk.NO_TRAVEL)], hours=1)
    b = route("B", [(10, Risk.NO_TRAVEL)], hours=1)
    rec = recommend([a, b])
    assert rec.best_id == "A"
    assert "Delay" in rec.warning


def test_ranking_orders_all_routes():
    a = route("A", [(10, Risk.SEVERE)], hours=1)
    b = route("B", [(10, Risk.HIGH)], hours=1)
    c = route("C", [(10, Risk.LOW)], hours=1)
    rec = recommend([a, b, c])
    assert rec.ranking == ["C", "B", "A"]
    assert rec.warning is None


def test_single_route():
    rec = recommend([route("A", [(10, Risk.LOW)], hours=1)])
    assert rec.best_id == "A"
    assert rec.reason == "Only route available."


def test_empty_list_raises():
    with pytest.raises(ValueError):
        recommend([])
