from dataclasses import dataclass
from datetime import timedelta

from .geo import METERS_PER_MILE, cumulative_distances, interp, point_at


@dataclass
class Checkpoint:
    mile: float
    lat: float
    lon: float
    eta: object
    segment_miles: float


def _clean_timing(timing, length_m, duration_s):
    # TomTom instruction offsets are monotonic in practice, but guard against
    # duplicates so interpolation never divides by zero or goes backwards.
    pairs = sorted({(0.0, 0.0), (float(length_m), float(duration_s)), *timing})
    xs, ys = [], []
    for m, s in pairs:
        if xs and (m <= xs[-1] or s < ys[-1]):
            continue
        xs.append(m)
        ys.append(s)
    return xs, ys


def sample_miles(total_miles, interval):
    marks = []
    m = 0.0
    while m < total_miles:
        marks.append(m)
        m += interval
    marks.append(total_miles)
    return marks


def build_checkpoints(points, length_m, duration_s, timing, departure, interval_miles):
    """Place a checkpoint every `interval_miles` plus one at the destination.

    Each checkpoint stands for the stretch of road halfway to its neighbours, so
    segment miles always add up to the route length.
    """
    cum = cumulative_distances(points)
    # Our haversine sum is a little off TomTom's road length; rescale to match it.
    scale = length_m / cum[-1] if cum[-1] else 1.0
    cum = [c * scale for c in cum]

    tx, ty = _clean_timing(timing, length_m, duration_s)
    total_miles = length_m / METERS_PER_MILE
    marks = sample_miles(total_miles, interval_miles)

    out = []
    for i, mile in enumerate(marks):
        meters = mile * METERS_PER_MILE
        lat, lon = point_at(points, cum, meters)
        secs = interp(tx, ty, meters)
        lo = (marks[i - 1] + mile) / 2 if i > 0 else 0.0
        hi = (mile + marks[i + 1]) / 2 if i < len(marks) - 1 else total_miles
        out.append(
            Checkpoint(
                mile=mile,
                lat=lat,
                lon=lon,
                eta=departure + timedelta(seconds=secs),
                segment_miles=hi - lo,
            )
        )
    return out
