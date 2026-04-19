from django.urls import path

from . import views

urlpatterns = [
    path("trips/plan/", views.plan_trip_view, name="plan-trip"),
    path("trips/<uuid:trip_id>/", views.get_trip_view, name="get-trip"),
    path("geocode/", views.geocode_view, name="geocode"),
]
