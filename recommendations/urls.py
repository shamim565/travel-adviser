from django.urls import path

from recommendations.views.district import TopDistrictListAPIView
from recommendations.views.recommendation import TravelRecommendationView

urlpatterns = [
    path("top-districts/", TopDistrictListAPIView.as_view(), name="top-districts"),
    path("recommendation/", TravelRecommendationView.as_view(), name="recommendation"),
]
