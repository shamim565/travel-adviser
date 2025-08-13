import logging
from celery import shared_task
from celery_singleton import Singleton

from .models import District
from recommendations.services.open_meteo import (
    fetch_weather,
    fetch_air_quality,
    weekly_avg_temperature_at_2pm,
    weekly_avg_pm25,
)

logger = logging.getLogger(__name__)


@shared_task(base=Singleton)
def update_district_weather_and_air_quality():
    """
    Periodic task to update average 2PM temperature and PM2.5 air quality for all districts.

    - Prevents overlapping runs using Singleton.
    - Updates `avg_temp_2pm` and `avg_pm2_5` in the District model.

    Runs every 60 minutes via Celery Beat.
    """
    districts = District.objects.all()
    updated_count = 0

    for district in districts:
        try:
            weather_json = fetch_weather(district.latitude, district.longitude)
            air_json = fetch_air_quality(district.latitude, district.longitude)

            temp = weekly_avg_temperature_at_2pm(weather_json)  # float | None
            pm25 = weekly_avg_pm25(air_json)  # float | None
        except Exception as e:
            logger.warning("Failed to fetch for %s: %s", district.name, e)
            continue

        if temp is not None and pm25 is not None:
            district.avg_temp_2pm = temp
            district.avg_pm2_5 = pm25
            district.save(update_fields=["avg_temp_2pm", "avg_pm2_5", "updated_at"])
            updated_count += 1

    logger.info(f"Updated weather data for {updated_count} districts.")
