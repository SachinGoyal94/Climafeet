import logging
from bisect import bisect_left, bisect_right
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

from .http import ProviderError, get_json

log = logging.getLogger(__name__)

URL = "https://api.open-meteo.com/v1/forecast"
HOURLY = ["wind_speed_10m", "wind_gusts_10m", "rain", "showers", "snowfall", "temperature_2m"]
BATCH = 100
GRID = 0.05  # degrees, roughly 3.5 miles. Close to the native model resolution.


def snap(lat, lon):
    return round(round(lat / GRID) * GRID, 2), round(round(lon / GRID) * GRID, 2)


@dataclass
class Sample:
    wind_mph: float
    gust_mph: float
    rain_in_hr: float
    snow_in_hr: float
    temp_f: float


@dataclass
class Series:
    times: list[int]
    wind: list[float]
    gust: list[float]
    rain: list[float]
    snow: list[float]
    temp: list[float]

    def at(self, ts):
        """Weather at unix time `ts`.

        Wind and temperature are instantaneous, so they are interpolated between
        the two surrounding hours. Rain and snow are totals for the hour ending
        at each timestamp, so we use the hour that contains `ts`.
        """
        t = self.times
        i = max(0, min(bisect_right(t, ts) - 1, len(t) - 1))
        j = min(i + 1, len(t) - 1)
        f = 0.0 if j == i else max(0.0, min(1.0, (ts - t[i]) / (t[j] - t[i])))

        def lerp(vals):
            return vals[i] + (vals[j] - vals[i]) * f

        k = min(bisect_left(t, ts), len(t) - 1)
        return Sample(
            wind_mph=lerp(self.wind),
            gust_mph=lerp(self.gust),
            rain_in_hr=self.rain[k],
            snow_in_hr=self.snow[k],
            temp_f=lerp(self.temp),
        )

    def to_compact(self):
        return [self.wind, self.gust, self.rain, self.snow, self.temp]


def _nums(values):
    return [float(v) if v is not None else 0.0 for v in values]


def _parse(block):
    h = block["hourly"]
    rain = _nums(h["rain"])
    showers = _nums(h.get("showers") or [0.0] * len(rain))
    return Series(
        times=[int(x) for x in h["time"]],
        wind=_nums(h["wind_speed_10m"]),
        gust=_nums(h["wind_gusts_10m"]),
        rain=[r + s for r, s in zip(rain, showers, strict=True)],
        snow=_nums(h["snowfall"]),
        temp=_nums(h["temperature_2m"]),
    )


def _fetch_batch(points, start_date, end_date):
    params = {
        "latitude": ",".join(f"{p[0]:.2f}" for p in points),
        "longitude": ",".join(f"{p[1]:.2f}" for p in points),
        "hourly": ",".join(HOURLY),
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "temperature_unit": "fahrenheit",
        "timezone": "UTC",
        "timeformat": "unixtime",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    resp, data = get_json(URL, params, "Open-Meteo")
    if data is None:
        if resp.status_code == 429:
            raise ProviderError(
                "Weather service rate limit reached. Wait a minute and try again.", status=503
            )
        reason = resp.text[:200]
        try:
            reason = resp.json().get("reason", reason)
        except ValueError:
            pass
        raise ProviderError(f"Weather lookup failed: {reason}")
    blocks = data if isinstance(data, list) else [data]
    return [_parse(b) for b in blocks]


def _cache_key(point, start_date, end_date):
    return f"wx:{point[0]}:{point[1]}:{start_date}:{end_date}"


def hourly_series(coords, start_date, end_date):
    """Return {snapped (lat, lon): Series} for every coordinate, using the cache
    and splitting misses into parallel batched requests."""
    unique = list(dict.fromkeys(snap(lat, lon) for lat, lon in coords))
    keys = {p: _cache_key(p, start_date, end_date) for p in unique}
    cached = cache.get_many(list(keys.values()))

    result = {p: cached[k] for p, k in keys.items() if k in cached}
    missing = [p for p in unique if p not in result]

    if missing:
        batches = [missing[i : i + BATCH] for i in range(0, len(missing), BATCH)]
        with ThreadPoolExecutor(max_workers=min(4, len(batches))) as pool:
            fetched = list(pool.map(lambda b: _fetch_batch(b, start_date, end_date), batches))
        fresh = {}
        for batch, series_list in zip(batches, fetched, strict=True):
            for p, s in zip(batch, series_list, strict=True):
                result[p] = s
                fresh[keys[p]] = s
        cache.set_many(fresh, timeout=settings.WEATHER_CACHE_SECONDS)
        log.info("weather: %d cached, %d fetched", len(unique) - len(missing), len(missing))

    return result
