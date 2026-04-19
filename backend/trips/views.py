"""API endpoints for trip planning."""
from __future__ import annotations

import logging
from datetime import datetime, timezone as _tz

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)
from rest_framework import status as http_status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from timezonefinder import TimezoneFinder

from .models import Trip
from .serializers import (
    GeocodeResponseSerializer,
    TripInputSerializer,
    TripSerializer,
)
from .services.geocoding import GeocodingError, autocomplete, geocode
from .services.hos_planner import (
    DROPOFF_HOURS,
    PICKUP_HOURS,
    Waypoint,
    plan_trip,
)
from .services.log_builder import build_daily_logs
from .services.routing import RoutingError, route_through

logger = logging.getLogger(__name__)
_TZ_FINDER = TimezoneFinder()

# Fallback average speed used only when the routing provider returns a zero
# duration (rare edge case on some ORS responses). 55 mph is the conventional
# planning speed for Class-8 trucks on US interstates.
_DEFAULT_AVERAGE_SPEED_MPH = 55.0


@extend_schema(
    tags=["trips"],
    summary="Plan a trip and generate daily log sheets",
    description=(
        "Geocodes the three addresses, builds a real road route (OSRM with "
        "ORS fallback), simulates the trip applying FMCSA Hours-of-Service "
        "rules, and returns the route geometry, required stops, segment "
        "timeline and FMCSA-style daily log entries. When `save=true` the "
        "whole plan is persisted and `trip_id` is included in the response."
    ),
    request=TripInputSerializer,
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Trip plan payload (see example).",
        ),
        400: OpenApiResponse(description="Validation or geocoding error."),
        502: OpenApiResponse(description="Upstream routing provider failure."),
    },
    examples=[
        OpenApiExample(
            "Green Bay → Chicago → Dallas",
            request_only=True,
            value={
                "current_location": "Green Bay, WI",
                "pickup_location": "Chicago, IL",
                "dropoff_location": "Dallas, TX",
                "current_cycle_used_hours": 10,
                "driver_name": "Ada Lovelace",
                "carrier_name": "Acme Freight",
                "save": False,
            },
        ),
    ],
)
@api_view(["POST"])
def plan_trip_view(request):
    serializer = TripInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        current = geocode(data["current_location"])
        pickup = geocode(data["pickup_location"])
        dropoff = geocode(data["dropoff_location"])
    except GeocodingError as exc:
        return Response({"detail": str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)

    try:
        route = route_through(
            [
                (current.latitude, current.longitude),
                (pickup.latitude, pickup.longitude),
                (dropoff.latitude, dropoff.longitude),
            ]
        )
    except RoutingError as exc:
        return Response({"detail": str(exc)}, status=http_status.HTTP_502_BAD_GATEWAY)

    total_miles = route.total_miles
    raw_drive_hours = route.total_hours or (total_miles / _DEFAULT_AVERAGE_SPEED_MPH)
    average_speed_mph = (
        total_miles / raw_drive_hours if raw_drive_hours else _DEFAULT_AVERAGE_SPEED_MPH
    )
    miles_to_pickup = route.legs[0].distance_miles

    waypoints = [
        Waypoint(
            miles_from_start=miles_to_pickup,
            label="Pickup",
            kind="pickup",
            on_duty_hours=PICKUP_HOURS,
            location_name=pickup.display_name,
            lat=pickup.latitude,
            lon=pickup.longitude,
        ),
        Waypoint(
            miles_from_start=total_miles,
            label="Dropoff",
            kind="dropoff",
            on_duty_hours=DROPOFF_HOURS,
            location_name=dropoff.display_name,
            lat=dropoff.latitude,
            lon=dropoff.longitude,
        ),
    ]

    departure = data.get("departure_time") or datetime.now(tz=_tz.utc)
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=_tz.utc)

    plan = plan_trip(
        departure=departure,
        total_miles=total_miles,
        average_speed_mph=average_speed_mph,
        current_cycle_used_hours=data["current_cycle_used_hours"],
        waypoints=waypoints,
        route_geometry=route.geometry,
    )

    tz_name = (
        _TZ_FINDER.timezone_at(lng=pickup.longitude, lat=pickup.latitude) or "UTC"
    )
    daily_logs = build_daily_logs(
        plan.segments,
        tz_name,
        driver_name=data.get("driver_name", ""),
        carrier_name=data.get("carrier_name", ""),
        home_terminal=pickup.display_name,
    )

    stops = _extract_stops(plan.segments, waypoints, route)

    payload = {
        "inputs": {
            "current_location": data["current_location"],
            "pickup_location": data["pickup_location"],
            "dropoff_location": data["dropoff_location"],
            "current_cycle_used_hours": data["current_cycle_used_hours"],
            "departure_time": departure.isoformat(),
        },
        "geocoded": {
            "current": current.to_dict(),
            "pickup": pickup.to_dict(),
            "dropoff": dropoff.to_dict(),
        },
        "timezone": tz_name,
        "summary": {
            "total_miles": round(total_miles, 2),
            "total_driving_hours": round(plan.total_driving_hours, 2),
            "total_on_duty_hours": round(plan.total_on_duty_hours, 2),
            "average_speed_mph": round(average_speed_mph, 1),
            "total_days": len(daily_logs),
            "cycle_used_hours_end": round(plan.cycle_used_hours_end, 2),
            "needs_restart": plan.needs_restart,
        },
        "route_geometry": route.geometry,
        "stops": stops,
        "segments": [s.to_dict() for s in plan.segments],
        "daily_logs": daily_logs,
    }

    if data.get("save"):
        trip = Trip.objects.create(
            current_location=data["current_location"],
            pickup_location=data["pickup_location"],
            dropoff_location=data["dropoff_location"],
            current_cycle_used_hours=data["current_cycle_used_hours"],
            departure_time=departure,
            timezone=tz_name,
            total_miles=total_miles,
            total_driving_hours=plan.total_driving_hours,
            total_on_duty_hours=plan.total_on_duty_hours,
            total_days=len(daily_logs),
            route_geometry=route.geometry,
            stops=stops,
            segments=payload["segments"],
            daily_logs=daily_logs,
            geocoded=payload["geocoded"],
        )
        payload["trip_id"] = str(trip.id)

    return Response(payload)


@extend_schema(
    tags=["trips"],
    summary="Retrieve a persisted trip plan",
    responses={
        200: TripSerializer,
        404: OpenApiResponse(description="Trip not found."),
    },
)
@api_view(["GET"])
def get_trip_view(_request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    return Response(TripSerializer(trip).data)


@extend_schema(
    tags=["geocoding"],
    summary="Address autocomplete (cached Nominatim proxy)",
    parameters=[
        OpenApiParameter(
            name="q",
            type=str,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Free-text query to look up.",
        ),
        OpenApiParameter(
            name="limit",
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Maximum suggestions to return (default 5).",
        ),
    ],
    responses={200: GeocodeResponseSerializer},
)
@api_view(["GET"])
def geocode_view(request):
    query = request.query_params.get("q", "")
    limit = int(request.query_params.get("limit", 5))
    return Response({"results": autocomplete(query, limit=limit)})


def _extract_stops(segments, waypoints, route) -> list[dict]:
    """Produce a compact list of notable stops for the map layer."""
    stops: list[dict] = []
    # Always include the start and the explicit waypoints.
    if route.geometry:
        stops.append(
            {
                "kind": "start",
                "label": "Current location",
                "lat": route.geometry[0][0],
                "lon": route.geometry[0][1],
            }
        )
    for wp in waypoints:
        stops.append(
            {
                "kind": wp.kind,
                "label": wp.label,
                "lat": wp.lat,
                "lon": wp.lon,
                "location_name": wp.location_name,
            }
        )

    for seg in segments:
        note = seg.note.lower()
        if "fuel" in note or "30-minute" in note or "10h rest" in note or "restart" in note:
            kind = (
                "fuel" if "fuel" in note
                else "break" if "30-minute" in note
                else "rest"
            )
            stops.append(
                {
                    "kind": kind,
                    "label": seg.note,
                    "lat": seg.lat,
                    "lon": seg.lon,
                    "at": seg.start.isoformat(),
                }
            )
    return stops
