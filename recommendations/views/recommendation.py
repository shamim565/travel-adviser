from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError

from recommendations.models import District
from recommendations.serializers.recommendation import (
    RecommendationQuerySerializer,
    TravelRecommendationResponseSerializer,
)

from recommendations.services.open_meteo import OpenMeteoService


def _qual_temp(delta: float) -> str:
    d = abs(delta)
    if d >= 5:
        return "significantly"
    if d >= 2:
        return "moderately"
    return "slightly"


def _qual_pm(delta: float) -> str:
    d = abs(delta)
    if d >= 20:
        return "significantly"
    if d >= 10:
        return "moderately"
    return "slightly"


@extend_schema(
    parameters=[RecommendationQuerySerializer],
    responses={200: TravelRecommendationResponseSerializer},
)
class TravelRecommendationView(APIView):
    """
    Compare 2 PM temperature and PM2.5 at the specified travel_date for:
    - current location (lat/lon)
    - destination district (its coordinates)

    Rule: Recommend only if destination is both cooler and has lower PM2.5.
    """

    def get(self, request):
        q = RecommendationQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        data = q.validated_data

        dest: District = data["destination_district"]
        travel_date = data["travel_date"]  # datetime.date
        measured_at = f"{travel_date.isoformat()}T14:00"

        # Build services
        current_service = OpenMeteoService(
            lat=data["current_lat"], lon=data["current_lon"]
        )
        dest_service = OpenMeteoService(lat=dest.latitude, lon=dest.longitude)

        # Fetch values at 2 PM local time for each location
        try:
            cur_temp = current_service.temperature_on(travel_date, hour=14)
            dest_temp = dest_service.temperature_on(travel_date, hour=14)
            cur_pm25 = current_service.pm25_on(travel_date, hour=14)
            dest_pm25 = dest_service.pm25_on(travel_date, hour=14)
        except Exception as e:
            raise ValidationError({"detail": str(e)})

        # Default outcome if we lack data
        recommendation = "Not Recommended"
        reason = "Insufficient data to compare temperature or air quality."

        temp_diff = None
        pm25_diff = None
        is_dest_cooler = False
        has_better_air = False

        if None not in (cur_temp, dest_temp, cur_pm25, dest_pm25):
            temp_diff = round(dest_temp - cur_temp, 1)  # negative => cooler
            pm25_diff = round(dest_pm25 - cur_pm25, 1)  # negative => cleaner
            is_dest_cooler = dest_temp < cur_temp
            has_better_air = dest_pm25 < cur_pm25

            if is_dest_cooler and has_better_air:
                recommendation = "Recommended"
                reason = (
                    f"Your destination is {abs(temp_diff)}°C {_qual_temp(temp_diff)} cooler "
                    f"and has {_qual_pm(pm25_diff)} better air quality. Enjoy your trip!"
                )
            else:
                parts = []
                if not is_dest_cooler:
                    parts.append(
                        "hotter"
                        if temp_diff is not None and temp_diff > 0
                        else "the same temperature"
                    )
                if not has_better_air:
                    parts.append(
                        "worse air quality"
                        if pm25_diff is not None and pm25_diff > 0
                        else "the same air quality"
                    )
                join = (
                    " and ".join(parts)
                    if parts
                    else "not better on temperature or air quality"
                )
                recommendation = "Not Recommended"
                reason = (
                    f"Your destination is {join} than your current location. "
                    f"It’s better to stay where you are."
                )

        payload = {
            "recommendation": recommendation,
            "reason": reason,
            "current": {
                "district": "",
                "lat": data["current_lat"],
                "lon": data["current_lon"],
                "temperature_c": cur_temp,
                "pm25": cur_pm25,
                "measured_at": measured_at,
            },
            "destination": {
                "district": getattr(dest, "name", str(dest.pk)),
                "lat": dest.latitude,
                "lon": dest.longitude,
                "temperature_c": dest_temp,
                "pm25": dest_pm25,
                "measured_at": measured_at,
            },
        }

        # Validate & return via response serializer for a tidy schema
        resp = TravelRecommendationResponseSerializer(data=payload)
        resp.is_valid(raise_exception=True)
        return Response(resp.data)
