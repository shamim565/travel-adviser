import os
from celery import Celery
from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


app.conf.beat_schedule = {
    "update-weather-and-air-quality": {
        "task": "recommendations.tasks.update_district_weather_and_air_quality",
        "schedule": timedelta(minutes=60),
    },
}
