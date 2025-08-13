from django.db import models
from django.contrib import admin

from .division import Division


class District(models.Model):
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    bn_name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()

    # Weather & Air Quality (updated periodically)
    avg_temp_2pm = models.FloatField(
        null=True, blank=True, help_text="Avg temp at 2 PM over 7 days"
    )
    avg_pm2_5 = models.FloatField(
        null=True, blank=True, help_text="Avg PM2.5 over 7 days"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "bn_name",
        "division_id",
        "latitude",
        "longitude",
        "avg_temp_2pm",
        "avg_pm2_5",
        "created_at",
        "updated_at",
    )
    search_fields = ("name", "bn_name")
    list_filter = ("division_id",)
