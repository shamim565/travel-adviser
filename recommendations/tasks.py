import logging
from celery import shared_task
from celery_singleton import Singleton

from .models import District
from .utils import fetch_weather, fetch_air_quality

logger = logging.getLogger(__name__)


@shared_task(base=Singleton)
def update_district_weather_and_air_quality():
    """
    Periodic task to update average 2PM temperature and PM2.5 air quality for all districts.

    - Prevents overlapping runs using Singleton.
    - Updates `avg_temp_2pm` and `avg_pm2_5` in the District model.

    Runs every 60 minutes via Celery Beat.
    """
    logger.info(f"Starting weather and air quality update task.")

    districts = District.objects.all()
    updated_count = 0

    for district in districts:
        try:
            temp = fetch_weather(district.latitude, district.longitude)
            pm25 = fetch_air_quality(district.latitude, district.longitude)
        except Exception as e:
            logger.warning(f"Failed to fetch for {district.name}: {e}")
            continue

        if temp is not None and pm25 is not None:
            district.avg_temp_2pm = temp
            district.avg_pm2_5 = pm25
            district.save(update_fields=["avg_temp_2pm", "avg_pm2_5", "updated_at"])
            updated_count += 1

    logger.info(f"Updated weather data for {updated_count} districts.")
