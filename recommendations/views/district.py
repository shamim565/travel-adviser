from rest_framework.generics import ListAPIView

from recommendations.models import District
from recommendations.serializers.district import DistrictSerializer


class TopDistrictListAPIView(ListAPIView):
    queryset = District.objects.all().order_by("avg_temp_2pm", "avg_pm2_5")[:10]
    serializer_class = DistrictSerializer
