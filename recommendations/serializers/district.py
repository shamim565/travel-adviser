from rest_framework import serializers

from recommendations.models import District


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = "__all__"
