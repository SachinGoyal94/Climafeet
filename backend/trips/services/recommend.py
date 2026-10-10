from dataclasses import dataclass

from .risk import Risk


@dataclass
class RiskSummary:
    miles: dict[Risk, float]
    total_miles: float
    avg_risk: float
    max_level: Risk


def summarize(segments):
    """segments: iterable of (miles, Risk) pairs covering the route."""
    miles = {level: 0.0 for level in Risk}
    weighted = 0.0
    for seg_miles, level in segments:
        miles[level] += seg_miles
        weighted += seg_miles * int(level)
    total = sum(miles.values())
    avg = weighted / total if total else 0.0
    worst = max((lvl for lvl, m in miles.items() if m > 0), default=Risk.LOW)
    return RiskSummary(miles=miles, total_miles=total, avg_risk=avg, max_level=worst)


@dataclass
class Candidate:
    id: str
    name: str
    duration_s: float
    risk: RiskSummary


@dataclass
class Recommendation:
    best_id: str
    ranking: list[str]
    reason: str
    warning: str | None


# No Travel miles are ranked ahead of Severe so that a route with a stretch that
# must not be driven never wins just because it has fewer Severe miles.
CRITERIA = [
    ("no_travel", "No Travel miles"),
    ("severe", "Severe miles"),
    ("high", "High miles"),
    ("avg", "average risk"),
    ("duration", "travel time"),
]


def _metrics(c):
    return {
        "no_travel": round(c.risk.miles[Risk.NO_TRAVEL], 1),
        "severe": round(c.risk.miles[Risk.SEVERE], 1),
        "high": round(c.risk.miles[Risk.HIGH], 1),
        "avg": round(c.risk.avg_risk, 3),
        "duration": round(c.duration_s),
    }


def sort_key(c):
    m = _metrics(c)
    return tuple(m[key] for key, _ in CRITERIA)


def _fmt(key, value):
    if key == "duration":
        minutes = round(value / 60)
        hours, mins = divmod(minutes, 60)
        return f"{hours}h {mins:02d}m" if hours else f"{mins} min"
    if key == "avg":
        return f"{value:.2f}"
    return f"{value:.0f} mi"


def _reason(best, runner_up):
    a, b = _metrics(best), _metrics(runner_up)
    for key, label in CRITERIA:
        if a[key] == b[key]:
            continue
        if key == "duration":
            saved = _fmt("duration", b[key] - a[key])
            return f"Same weather risk as {runner_up.name}, but {saved} faster."
        word = "Lowest" if key == "avg" else "Fewest"
        return f"{word} {label}: {_fmt(key, a[key])} vs {_fmt(key, b[key])} on {runner_up.name}."
    return f"Ties with {runner_up.name} on every criterion."


def recommend(candidates):
    if not candidates:
        raise ValueError("no routes to compare")

    ranked = sorted(candidates, key=sort_key)
    best = ranked[0]

    reason = _reason(best, ranked[1]) if len(ranked) > 1 else "Only route available."

    warning = None
    if best.risk.miles[Risk.NO_TRAVEL] > 0:
        warning = (
            "Every route crosses No Travel conditions for this load. "
            "Delay the departure or reduce the load."
        )
    elif best.risk.miles[Risk.SEVERE] > 0:
        warning = "Recommended route still has Severe weather. Drive with extra caution."

    return Recommendation(
        best_id=best.id,
        ranking=[c.id for c in ranked],
        reason=reason,
        warning=warning,
    )
