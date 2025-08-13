from django.urls import path

from recommendations.views.district import TopDistrictListAPIView

urlpatterns = [
    path("top-districts/", TopDistrictListAPIView.as_view(), name="top-districts"),
]
