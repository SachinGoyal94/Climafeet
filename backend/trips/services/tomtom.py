import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from django.conf import settings

from .geo import bearing, cumulative_distances, haversine_m, offset_point, point_at
from .http import ProviderError, get_json

log = logging.getLogger(__name__)

BASE = "https://api.tomtom.com"
LB_TO_KG = 0.45359237


@dataclass
class Place:
    lat: float
    lon: float
    label: str


@dataclass
class RawRoute:
    points: list[tuple[float, float]]
    length_m: float
    duration_s: float
    traffic_delay_s: float
    timing: list[tuple[float, float]] = field(default_factory=list)
    via: tuple[float, float] | None = None


def _key():
    if not settings.TOMTOM_API_KEY:
        raise ProviderError("TOMTOM_API_KEY is not configured on the server.", status=500)
    return settings.TOMTOM_API_KEY


def _error_text(resp):
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:200]
    err = body.get("detailedError") or body.get("error") or {}
    return err.get("message") or err.get("description") or str(body)[:200]


def geocode(query, limit=5):
    url = f"{BASE}/search/2/search/{quote(query)}.json"
    params = {"key": _key(), "limit": limit, "typeahead": "true"}
    resp, data = get_json(url, params, "TomTom Search")
    if data is None:
        raise ProviderError(f"Geocoding failed: {_error_text(resp)}")

    places = []
    for r in data.get("results", []):
        pos = r.get("position") or {}
        addr = r.get("address") or {}
        name = (r.get("poi") or {}).get("name")
        label = addr.get("freeformAddress") or ""
        if name and name not in label:
            label = f"{name}, {label}"
        if "lat" in pos and "lon" in pos and label:
            places.append(Place(pos["lat"], pos["lon"], label))
    return places


def _depart_param(depart_at):
    # TomTom rejects departAt values in the past
    if depart_at <= datetime.now(UTC) + timedelta(minutes=1):
        return "now"
    return depart_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_route(r, via=None):
    points = [(p["latitude"], p["longitude"]) for leg in r["legs"] for p in leg["points"]]
    summary = r["summary"]
    timing = [
        (float(ins["routeOffsetInMeters"]), float(ins["travelTimeInSeconds"]))
        for ins in (r.get("guidance") or {}).get("instructions", [])
        if "routeOffsetInMeters" in ins and "travelTimeInSeconds" in ins
    ]
    return RawRoute(
        points=points,
        length_m=float(summary["lengthInMeters"]),
        duration_s=float(summary["travelTimeInSeconds"]),
        traffic_delay_s=float(summary.get("trafficDelayInSeconds", 0)),
        timing=timing,
        via=via,
    )


def _calculate(stops, depart_at, load_lb, alternatives):
    path = ":".join(f"{lat:.6f},{lon:.6f}" for lat, lon in stops)
    params = {
        "key": _key(),
        "travelMode": "truck",
        "vehicleCommercial": "true",
        "vehicleWeight": round(load_lb * LB_TO_KG),
        "routeType": "fastest",
        "traffic": "true",
        "departAt": _depart_param(depart_at),
        "instructionsType": "coded",
    }
    if alternatives:
        params["maxAlternatives"] = alternatives
    resp, data = get_json(f"{BASE}/routing/1/calculateRoute/{path}/json", params, "TomTom Routing")
    if data is None:
        msg = _error_text(resp)
        status = 422 if resp.status_code == 400 else 502
        raise ProviderError(f"Routing failed: {msg}", status=status)
    via = stops[1] if len(stops) == 3 else None
    return [_parse_route(r, via) for r in data.get("routes", [])]


def _is_duplicate(route, existing):
    for other in existing:
        if (
            abs(route.length_m - other.length_m) / other.length_m < 0.01
            and abs(route.duration_s - other.duration_s) / max(other.duration_s, 1) < 0.01
        ):
            return True
    return False


def _via_points(main, origin, dest):
    """Points pushed sideways off the middle of the main route, used to force
    TomTom into distinct corridors when it returns fewer than 3 alternatives."""
    cum = cumulative_distances(main.points)
    mid_lat, mid_lon = point_at(main.points, cum, cum[-1] / 2)
    heading = bearing(origin.lat, origin.lon, dest.lat, dest.lon)
    straight = haversine_m(origin.lat, origin.lon, dest.lat, dest.lon)
    shift = min(max(straight * 0.15, 15_000), 120_000)
    return [offset_point(mid_lat, mid_lon, heading + side, shift) for side in (90, -90)]


def truck_routes(origin, dest, depart_at, load_lb, wanted=3):
    a, b = (origin.lat, origin.lon), (dest.lat, dest.lon)
    routes = _calculate([a, b], depart_at, load_lb, alternatives=wanted - 1)
    if not routes:
        raise ProviderError("No truck route found between these places.", status=422)

    if len(routes) < wanted:
        vias = _via_points(routes[0], origin, dest)
        with ThreadPoolExecutor(max_workers=len(vias)) as pool:
            futures = [pool.submit(_calculate, [a, v, b], depart_at, load_lb, 0) for v in vias]
            for fut in futures:
                try:
                    extra = fut.result()
                except ProviderError as exc:
                    log.info("via route skipped: %s", exc.message)
                    continue
                for r in extra:
                    if len(routes) < wanted and not _is_duplicate(r, routes):
                        routes.append(r)

    return routes[:wanted]
