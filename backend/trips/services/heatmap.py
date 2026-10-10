import math
from datetime import UTC, timedelta

from .geo import cumulative_distances, point_at
from .risk import assess
from .weather import hourly_series, snap

HOURS = 48
MAX_CELLS = 900
KM_PER_DEG = 111.32


def _resample(line, spacing_km):
    """Points every `spacing_km` along a [(lat, lon), ...] polyline."""
    if len(line) < 2:
        return list(line)
    cum = cumulative_distances(line)
    step = spacing_km * 1000
    n = max(1, int(cum[-1] // step))
    return [point_at(line, cum, i * step) for i in range(n + 1)] + [line[-1]]


def corridor_cells(lines, step_deg=None, buffer_km=None):
    """Grid cell centres within `buffer_km` of any route line.

    Works by stamping a disc of cells around points sampled along each line,
    which is far cheaper than measuring every cell against every segment.
    """
    total_km = max(cumulative_distances(line)[-1] for line in lines) / 1000
    step = step_deg or min(max(total_km / 60 / KM_PER_DEG, 0.1), 0.6)

    while True:
        buf = buffer_km or max(40.0, step * KM_PER_DEG * 2.5)
        cells = set()
        for line in lines:
            for lat, lon in _resample(line, step * KM_PER_DEG / 2):
                kx = 1 / max(math.cos(math.radians(lat)), 0.2)
                ry = buf / KM_PER_DEG
                rx = ry * kx
                i0, i1 = math.floor((lat - ry) / step), math.ceil((lat + ry) / step)
                j0, j1 = math.floor((lon - rx) / step), math.ceil((lon + rx) / step)
                for i in range(i0, i1 + 1):
                    dy = (i * step - lat) / ry
                    for j in range(j0, j1 + 1):
                        dx = (j * step - lon) / rx
                        if dx * dx + dy * dy <= 1:
                            cells.add((i, j))
        if len(cells) <= MAX_CELLS or step_deg:
            break
        step *= 1.25

    pts = sorted((round(i * step, 4), round(j * step, 4)) for i, j in cells)
    return pts, step


def build_heatmap(lines, start, load_lb):
    """lines: list of [(lat, lon), ...]. Returns hourly grids for hours 0..48 after start."""
    start = start.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=HOURS)
    cells, step = corridor_cells(lines)

    series = hourly_series(cells, start.date(), end.date())

    risk, wind, rain, snow = [], [], [], []
    for h in range(HOURS + 1):
        ts = (start + timedelta(hours=h)).timestamp()
        r_row, w_row, p_row, s_row = [], [], [], []
        for lat, lon in cells:
            wx = series[snap(lat, lon)].at(ts)
            r_row.append(int(assess(wx.wind_mph, wx.rain_in_hr, wx.snow_in_hr, load_lb).level))
            w_row.append(round(wx.wind_mph, 1))
            p_row.append(round(wx.rain_in_hr, 3))
            s_row.append(round(wx.snow_in_hr, 3))
        risk.append(r_row)
        wind.append(w_row)
        rain.append(p_row)
        snow.append(s_row)

    return {
        "start": start.isoformat(),
        "hours": HOURS,
        "step_deg": round(step, 4),
        "cells": [[lon, lat] for lat, lon in cells],
        "risk": risk,
        "wind_mph": wind,
        "rain_in_hr": rain,
        "snow_in_hr": snow,
    }
