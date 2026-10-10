from dataclasses import dataclass, field
from enum import IntEnum


class Risk(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self):
        return _LABELS[self]


_LABELS = {
    Risk.LOW: "Low",
    Risk.MODERATE: "Moderate",
    Risk.HIGH: "High",
    Risk.SEVERE: "Severe",
    Risk.NO_TRAVEL: "No Travel",
}

# (lower bound, level, inclusive). Checked from the top down, first match wins.
# Ranges in the spec share their edges (0.10-0.25, 0.25-0.50), so a value sitting
# on an edge goes to the higher band. The top band uses the spec's strict ">".
WIND_MPH = [
    (55, Risk.NO_TRAVEL, True),
    (45, Risk.SEVERE, True),
    (35, Risk.HIGH, True),
    (25, Risk.MODERATE, True),
]
RAIN_IN_HR = [
    (1.00, Risk.NO_TRAVEL, False),
    (0.50, Risk.SEVERE, True),
    (0.25, Risk.HIGH, True),
    (0.10, Risk.MODERATE, True),
]
SNOW_IN_HR = [
    (3.0, Risk.NO_TRAVEL, False),
    (2.0, Risk.SEVERE, True),
    (1.0, Risk.HIGH, True),
    (0.5, Risk.MODERATE, True),
]


def _classify(value, bands):
    for bound, level, inclusive in bands:
        if value > bound or (inclusive and value == bound):
            return level
    return Risk.LOW


def wind_level(mph):
    return _classify(mph, WIND_MPH)


def rain_level(in_per_hr):
    return _classify(in_per_hr, RAIN_IN_HR)


def snow_level(in_per_hr):
    return _classify(in_per_hr, SNOW_IN_HR)


def load_level(wind_mph, load_lb):
    if wind_mph >= 55:
        return Risk.NO_TRAVEL
    if 45 <= wind_mph < 55 and load_lb > 30_000:
        return Risk.NO_TRAVEL
    if 35 <= wind_mph < 45 and load_lb > 40_000:
        return Risk.SEVERE
    return Risk.LOW


@dataclass
class Assessment:
    level: Risk
    wind: Risk
    rain: Risk
    snow: Risk
    load: Risk
    reasons: list[str] = field(default_factory=list)


def assess(wind_mph, rain_in_hr, snow_in_hr, load_lb):
    wind = wind_level(wind_mph)
    rain = rain_level(rain_in_hr)
    snow = snow_level(snow_in_hr)
    load = load_level(wind_mph, load_lb)
    level = max(wind, rain, snow, load)

    reasons = []
    if level > Risk.LOW:
        if wind == level:
            reasons.append(f"Wind {wind_mph:.0f} mph")
        if rain == level:
            reasons.append(f"Rain {rain_in_hr:.2f} in/hr")
        if snow == level:
            reasons.append(f"Snow {snow_in_hr:.2f} in/hr")
        if load == level and load > wind:
            reasons.append(f"Wind {wind_mph:.0f} mph with {load_lb:,.0f} lb load")

    return Assessment(level, wind, rain, snow, load, reasons)
