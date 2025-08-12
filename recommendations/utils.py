import requests
from decouple import config
from collections import defaultdict
from tenacity import retry, wait_exponential, stop_after_attempt

WEATHER_URL = config(
    "WEATHER_FORECAST_URL", default="https://api.open-meteo.com/v1/forecast"
)
AIR_QUALITY_URL = config(
    "AIR_QUALITY_URL", default="https://air-quality-api.open-meteo.com/v1/air-quality"
)


# Retry config: max 3 attempts, exponential backoff (1s, 2s, 4s)
@retry(wait=wait_exponential(multiplier=1, min=1, max=4), stop=stop_after_attempt(3))
def fetch_weather(lat: float, lon: float):
    """
    Fetches hourly temperature data for the next 7 days from the Open-Meteo weather API
    and computes the average temperature at 2 PM for the entire forecast period.

    Args:
        lat (float): Latitude of the location.
        lon (float): Longitude of the location.

    Returns:
        float or None: Average temperature at 2 PM over 7 days, rounded to 1 decimal place.
                       Returns None if no data is available.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m",
        "forecast_days": 7,
        "timezone": "auto",
    }
    response = requests.get(WEATHER_URL, params=params)
    response.raise_for_status()
    data = response.json()

    times = data["hourly"]["time"]
    temps = data["hourly"]["temperature_2m"]

    # Get 2PM values
    two_pm_temps = [temps[i] for i, t in enumerate(times) if "14:00" in t]
    avg_temp = round(sum(two_pm_temps) / len(two_pm_temps), 1) if two_pm_temps else None

    return avg_temp


@retry(wait=wait_exponential(multiplier=1, min=1, max=4), stop=stop_after_attempt(3))
def fetch_air_quality(lat: float, lon: float):
    """
    Fetches hourly PM2.5 air quality data for the next 7 days from the Open-Meteo air quality API.
    Computes the daily average PM2.5 for each day, then returns the average of these daily averages.

    Args:
        lat (float): Latitude of the location.
        lon (float): Longitude of the location.

    Returns:
        float or None: Weekly average PM2.5 value (in µg/m³), rounded to 1 decimal place.
                       Returns None if no data is available.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "pm2_5",
        "forecast_days": 7,
    }
    response = requests.get(AIR_QUALITY_URL, params=params)
    response.raise_for_status()
    data = response.json()

    times = data["hourly"]["time"]
    pm25s = data["hourly"]["pm2_5"]

    # Group PM2.5 values by date
    daily_data = defaultdict(list)
    for t, pm25 in zip(times, pm25s):
        if pm25 is not None:
            date = t.split("T")[0]
            daily_data[date].append(pm25)

    # Calculate daily averages
    daily_averages = []
    for date, values in daily_data.items():
        avg = sum(values) / len(values)
        daily_averages.append(avg)

    # Calculate weekly average
    weekly_avg_pm25 = (
        round(sum(daily_averages) / len(daily_averages), 1) if daily_averages else None
    )

    return weekly_avg_pm25
