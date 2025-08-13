from __future__ import annotations

from django.core.cache import cache
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple, Iterable

import requests
from decouple import config
from tenacity import retry, wait_exponential, stop_after_attempt

WEATHER_URL = config(
    "WEATHER_FORECAST_URL", default="https://api.open-meteo.com/v1/forecast"
)
AIR_QUALITY_URL = config(
    "AIR_QUALITY_URL", default="https://air-quality-api.open-meteo.com/v1/air-quality"
)

# TTLs (seconds)
WEATHER_CACHE_TTL = config("WEATHER_CACHE_TTL", default=1800, cast=int)  # 30 min
AIR_QUALITY_CACHE_TTL = config("AIR_QUALITY_CACHE_TTL", default=1800, cast=int)

# Retry: 1s, 2s, 4s; up to 3 attempts total
_retry = dict(
    wait=wait_exponential(multiplier=1, min=1, max=4), stop=stop_after_attempt(3)
)

_CACHE_SENTINEL = object()


def _norm_coords(lat: float, lon: float, precision: int = 2):
    """Round coords to reduce cache cardinality (~1.1 km at 2 dp)."""
    return round(float(lat), precision), round(float(lon), precision)


def _cache_key(
    prefix: str, lat: float, lon: float, *, precision: int = 2, extra: str = ""
) -> str:
    lat_n, lon_n = _norm_coords(lat, lon, precision)
    return f"{prefix}:{lat_n:.{precision}f},{lon_n:.{precision}f}:{extra}"


@retry(**_retry)
def fetch_weather(
    lat: float,
    lon: float,
    *,
    forecast_days: int = 7,
    timezone: str = "auto",
) -> dict:
    """Fetch raw weather JSON from Open-Meteo (hourly temperature_2m)."""
    key = _cache_key(
        "openmeteo:weather",
        lat,
        lon,
        extra=f"fd={forecast_days}|tz={timezone}",
    )
    cached = cache.get(key, _CACHE_SENTINEL)
    if cached is not _CACHE_SENTINEL:
        return cached

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m",
        "forecast_days": forecast_days,
        "timezone": timezone,
    }
    resp = requests.get(WEATHER_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    cache.set(key, data, timeout=WEATHER_CACHE_TTL)
    return data


@retry(**_retry)
def fetch_air_quality(
    lat: float,
    lon: float,
    *,
    forecast_days: int = 7,
) -> dict:
    """Fetch raw air-quality JSON from Open-Meteo (hourly pm2_5)."""
    key = _cache_key(
        "openmeteo:air_quality",
        lat,
        lon,
        extra=f"fd={forecast_days}",
    )
    cached = cache.get(key, _CACHE_SENTINEL)
    if cached is not _CACHE_SENTINEL:
        return cached

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "pm2_5",
        "forecast_days": forecast_days,
    }
    resp = requests.get(AIR_QUALITY_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    cache.set(key, data, timeout=AIR_QUALITY_CACHE_TTL)
    return data


# ---------------------------
# Parsing helpers
# ---------------------------


def _hourly_series(payload: dict, field: str) -> List[Tuple[str, Optional[float]]]:
    """
    Return list of (timestamp, value) for the given hourly field.
    `timestamp` is an ISO-like string from the API, e.g. '2025-08-13T14:00'.
    """
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    values = hourly.get(field) or []
    return list(zip(times, values))


def hourly_map(payload: dict, field: str) -> Dict[str, Optional[float]]:
    """Datetime-wise data: map 'YYYY-MM-DDTHH:MM' -> value (may include None)."""
    return dict(_hourly_series(payload, field))


def value_on_date_at_hour(
    payload: dict, field: str, d: date, hour: int
) -> Optional[float]:
    """
    Get value for a specific `date` at `hour` (0-23).
    Returns None if not present.
    """
    needle = f"{d.isoformat()}T{hour:02d}:00"
    return hourly_map(payload, field).get(needle)


def _values_at_hour(payload: dict, field: str, hour: int) -> List[float]:
    """Collect all non-None values for entries where time ends with 'THH:00'."""
    series = _hourly_series(payload, field)
    suffix = f"T{hour:02d}:00"
    return [v for t, v in series if t.endswith(suffix) and v is not None]


def _daily_groups(
    values: Iterable[Tuple[str, Optional[float]]],
) -> Dict[str, List[float]]:
    """
    Group (time_str, value) pairs by 'YYYY-MM-DD', skipping None values.
    Returns: {date_str: [values...]}
    """
    out: Dict[str, List[float]] = defaultdict(list)
    for t, v in values:
        if v is None:
            continue
        day = t.split("T", 1)[0]
        out[day].append(v)
    return out


def _avg(nums: List[float]) -> Optional[float]:
    return round(sum(nums) / len(nums), 1) if nums else None


# ---------------------------
# Domain-specific aggregations
# ---------------------------


def weekly_avg_temperature_at_2pm(weather_json: dict) -> Optional[float]:
    """
    Average of all 2 PM temperature_2m values across the forecast window.
    Returns float (°C, 1 dp) or None if no data.
    """
    vals = _values_at_hour(weather_json, field="temperature_2m", hour=14)
    return _avg(vals)


def weekly_avg_pm25(air_json: dict) -> Optional[float]:
    """
    Daily-average PM2.5 across the forecast window, then average those daily averages.
    Returns float (µg/m³, 1 dp) or None if no data.
    """
    series = _hourly_series(air_json, field="pm2_5")
    by_day = _daily_groups(series)

    # daily averages
    daily_avgs: List[float] = []
    for _day, values in by_day.items():
        if values:
            daily_avgs.append(sum(values) / len(values))

    return _avg(daily_avgs)


@dataclass
class OpenMeteoService:
    lat: float
    lon: float

    def fetch_weather(self) -> dict:
        return fetch_weather(self.lat, self.lon)

    def fetch_air_quality(self) -> dict:
        return fetch_air_quality(self.lat, self.lon)

    # datetime-wise maps
    def weather_timeseries(self) -> Dict[str, Optional[float]]:
        return hourly_map(self.fetch_weather(), "temperature_2m")

    def air_quality_timeseries(self) -> Dict[str, Optional[float]]:
        return hourly_map(self.fetch_air_quality(), "pm2_5")

    # point lookups
    def temperature_on(self, d: date, hour: int = 14) -> Optional[float]:
        return value_on_date_at_hour(self.fetch_weather(), "temperature_2m", d, hour)

    def pm25_on(self, d: date, hour: int) -> Optional[float]:
        return value_on_date_at_hour(self.fetch_air_quality(), "pm2_5", d, hour)

    # weekly aggregates
    def weekly_avg_temp_2pm(self) -> Optional[float]:
        return weekly_avg_temperature_at_2pm(self.fetch_weather())

    def weekly_avg_pm25(self) -> Optional[float]:
        return weekly_avg_pm25(self.fetch_air_quality())
