from django.utils import timezone
from rest_framework import serializers

from recommendations.models import District


class RecommendationQuerySerializer(serializers.Serializer):
    """
    Query params:
      - current_lat, current_lon: coordinates of current location
      - destination_district: ID of the destination district
      - travel_date: planned travel date
    """

    current_lat = serializers.FloatField(min_value=-90, max_value=90)
    current_lon = serializers.FloatField(min_value=-180, max_value=180)
    destination_district = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.all()
    )
    travel_date = serializers.DateField()

    def validate_travel_date(self, value):
        # Don’t allow dates in the past
        today = timezone.localdate()
        if value < today:
            raise serializers.ValidationError("travel_date cannot be in the past.")
        return value


RECOMMENDATION_CHOICES = ("Recommended", "Not Recommended")


class LocationMetricsSerializer(serializers.Serializer):
    temperature_c = serializers.FloatField(allow_null=True)
    pm25 = serializers.FloatField(allow_null=True)
    measured_at = serializers.CharField()
    district = serializers.CharField(required=False, allow_blank=True)
    lat = serializers.FloatField(required=False)
    lon = serializers.FloatField(required=False)


class TravelRecommendationResponseSerializer(serializers.Serializer):
    recommendation = serializers.ChoiceField(choices=RECOMMENDATION_CHOICES)
    reason = serializers.CharField()
    current = LocationMetricsSerializer()
    destination = LocationMetricsSerializer()
