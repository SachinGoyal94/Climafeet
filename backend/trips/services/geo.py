import math
from bisect import bisect_right

EARTH_RADIUS_M = 6_371_008.8
METERS_PER_MILE = 1609.344


def haversine_m(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def cumulative_distances(points):
    out = [0.0]
    for (lat1, lon1), (lat2, lon2) in zip(points, points[1:], strict=False):
        out.append(out[-1] + haversine_m(lat1, lon1, lat2, lon2))
    return out


def point_at(points, cum, distance):
    if distance <= 0:
        return points[0]
    if distance >= cum[-1]:
        return points[-1]
    i = bisect_right(cum, distance) - 1
    span = cum[i + 1] - cum[i]
    t = (distance - cum[i]) / span if span else 0.0
    (lat1, lon1), (lat2, lon2) = points[i], points[i + 1]
    return lat1 + (lat2 - lat1) * t, lon1 + (lon2 - lon1) * t


def interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    i = bisect_right(xs, x) - 1
    span = xs[i + 1] - xs[i]
    t = (x - xs[i]) / span if span else 0.0
    return ys[i] + (ys[i + 1] - ys[i]) * t


def offset_point(lat, lon, bearing_deg, distance_m):
    d = distance_m / EARTH_RADIUS_M
    b = math.radians(bearing_deg)
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(
        math.sin(b) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2)
    )
    return math.degrees(p2), (math.degrees(l2) + 540) % 360 - 180


def bearing(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def simplify(points, tolerance_deg=0.0003):
    """Ramer-Douglas-Peucker. Cuts route payloads by ~90% with no visible change."""
    if len(points) < 3:
        return list(points)

    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    tol2 = tolerance_deg**2

    while stack:
        start, end = stack.pop()
        (ay, ax), (by, bx) = points[start], points[end]
        k = math.cos(math.radians((ay + by) / 2))
        ax, bx = ax * k, bx * k
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy

        worst, worst_d2 = -1, tol2
        for i in range(start + 1, end):
            py, px = points[i]
            px *= k
            if seg2 == 0:
                d2 = (px - ax) ** 2 + (py - ay) ** 2
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
                d2 = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
            if d2 > worst_d2:
                worst, worst_d2 = i, d2

        if worst != -1:
            keep[worst] = True
            stack.append((start, worst))
            stack.append((worst, end))

    return [p for p, k in zip(points, keep, strict=True) if k]
