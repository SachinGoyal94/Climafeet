from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from .checkpoints import build_checkpoints
from .geo import METERS_PER_MILE, simplify
from .http import ProviderError
from .recommend import Candidate, recommend, summarize
from .risk import Risk, assess
from .tomtom import Place, geocode, truck_routes
from .weather import hourly_series, snap

ROUTE_IDS = "ABC"
FORECAST_DAYS = 15


def resolve_place(data):
    if data.get("lat") is not None and data.get("lon") is not None:
        return Place(data["lat"], data["lon"], data.get("label") or "")
    matches = geocode(data["label"], limit=1)
    if not matches:
        raise ProviderError(f"Could not find a place called '{data['label']}'.", status=422)
    return matches[0]


def _r(x, n=2):
    return round(x, n)


def _summary_json(s):
    return {
        "miles": {lvl.label: _r(s.miles[lvl], 1) for lvl in Risk},
        "avg_risk": _r(s.avg_risk, 3),
        "max_level": int(s.max_level),
        "max_label": s.max_level.label,
    }


def _bbox(routes):
    lats = [p[0] for r in routes for p in r.points]
    lons = [p[1] for r in routes for p in r.points]
    return [min(lons), min(lats), max(lons), max(lats)]


def plan_trip(origin, destination, departure, load_lb, interval_miles):
    now = datetime.now(UTC)
    departure = max(departure.astimezone(UTC), now).replace(microsecond=0)

    with ThreadPoolExecutor(max_workers=2) as pool:
        o, d = pool.map(resolve_place, [origin, destination])

    raw = truck_routes(o, d, departure, load_lb)

    per_route = [
        build_checkpoints(r.points, r.length_m, r.duration_s, r.timing, departure, interval_miles)
        for r in raw
    ]

    last_eta = max(cp.eta for cps in per_route for cp in cps)
    if last_eta.date() > (now + timedelta(days=FORECAST_DAYS)).date():
        raise ProviderError(
            "This trip ends beyond the 16 day forecast window. Pick an earlier departure.",
            status=422,
        )

    coords = [(cp.lat, cp.lon) for cps in per_route for cp in cps]
    series = hourly_series(coords, departure.date(), last_eta.date())

    routes_json, candidates = [], []
    for idx, (route, cps) in enumerate(zip(raw, per_route, strict=True)):
        rid = ROUTE_IDS[idx]
        cp_json, segments = [], []
        for cp in cps:
            wx = series[snap(cp.lat, cp.lon)].at(cp.eta.timestamp())
            a = assess(wx.wind_mph, wx.rain_in_hr, wx.snow_in_hr, load_lb)
            segments.append((cp.segment_miles, a.level))
            cp_json.append(
                {
                    "mile": _r(cp.mile, 1),
                    "lat": _r(cp.lat, 5),
                    "lon": _r(cp.lon, 5),
                    "eta": cp.eta.replace(microsecond=0).isoformat(),
                    "segment_miles": _r(cp.segment_miles),
                    "weather": {
                        "wind_mph": _r(wx.wind_mph, 1),
                        "gust_mph": _r(wx.gust_mph, 1),
                        "rain_in_hr": _r(wx.rain_in_hr, 3),
                        "snow_in_hr": _r(wx.snow_in_hr, 3),
                        "temp_f": _r(wx.temp_f, 1),
                    },
                    "level": int(a.level),
                    "label": a.level.label,
                    "reasons": a.reasons,
                }
            )

        summary = summarize(segments)
        candidates.append(Candidate(rid, f"Route {rid}", route.duration_s, summary))
        routes_json.append(
            {
                "id": rid,
                "name": f"Route {rid}",
                "distance_miles": _r(route.length_m / METERS_PER_MILE, 1),
                "duration_s": round(route.duration_s),
                "traffic_delay_s": round(route.traffic_delay_s),
                "departure": departure.isoformat(),
                "arrival": (departure + timedelta(seconds=route.duration_s)).isoformat(),
                "geometry": [[_r(lon, 5), _r(lat, 5)] for lat, lon in simplify(route.points)],
                "summary": _summary_json(summary),
                "checkpoints": cp_json,
            }
        )

    rec = recommend(candidates)
    order = {rid: i for i, rid in enumerate(rec.ranking)}
    for r in routes_json:
        r["rank"] = order[r["id"]] + 1
        r["recommended"] = r["id"] == rec.best_id

    return {
        "origin": {"lat": o.lat, "lon": o.lon, "label": o.label or origin.get("label", "")},
        "destination": {
            "lat": d.lat,
            "lon": d.lon,
            "label": d.label or destination.get("label", ""),
        },
        "departure": departure.isoformat(),
        "load_lb": load_lb,
        "interval_miles": interval_miles,
        "bbox": _bbox(raw),
        "routes": routes_json,
        "recommendation": {
            "best_id": rec.best_id,
            "ranking": rec.ranking,
            "reason": rec.reason,
            "warning": rec.warning,
        },
    }
