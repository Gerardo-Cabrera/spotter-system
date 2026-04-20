"""Tests for the ``_extract_stops`` helper that powers the map + itinerary.

The frontend `Itinerary` component relies on every stop carrying an ``at``
timestamp in order to render a real chronological timeline. These tests
pin that invariant.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from trips.services.hos_planner import (
    DROPOFF_HOURS,
    PICKUP_HOURS,
    Waypoint,
    plan_trip,
)
from trips.views import _extract_stops

DEPARTURE = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)


def _build_plan_and_route(total_miles: float, miles_to_pickup: float, speed: float):
    waypoints = [
        Waypoint(miles_to_pickup, "Pickup", "pickup", PICKUP_HOURS, "P", 41.0, -87.0),
        Waypoint(total_miles, "Dropoff", "dropoff", DROPOFF_HOURS, "D", 32.0, -96.0),
    ]
    plan = plan_trip(
        departure=DEPARTURE,
        total_miles=total_miles,
        average_speed_mph=speed,
        current_cycle_used_hours=0,
        waypoints=waypoints,
        route_geometry=[[44.5, -88.0], [41.0, -87.0], [32.0, -96.0]],
    )
    route = SimpleNamespace(geometry=[[44.5, -88.0], [41.0, -87.0], [32.0, -96.0]])
    return plan, waypoints, route


def test_every_stop_has_an_iso_timestamp():
    """start / pickup / dropoff / fuel / break / rest must all carry `at`."""
    plan, waypoints, route = _build_plan_and_route(
        total_miles=1200, miles_to_pickup=100, speed=55
    )
    stops = _extract_stops(plan.segments, waypoints, route)

    assert stops, "Expected at least start + pickup + dropoff"
    for stop in stops:
        assert stop.get("at"), f"stop {stop['kind']} missing `at`: {stop!r}"
        # Must be parseable as ISO 8601.
        datetime.fromisoformat(stop["at"])


def test_pickup_and_dropoff_times_are_chronological():
    plan, waypoints, route = _build_plan_and_route(
        total_miles=400, miles_to_pickup=80, speed=55
    )
    stops = _extract_stops(plan.segments, waypoints, route)

    by_kind = {s["kind"]: datetime.fromisoformat(s["at"]) for s in stops}
    assert by_kind["start"] <= by_kind["pickup"] < by_kind["dropoff"]


def test_start_stop_matches_first_segment_start():
    plan, waypoints, route = _build_plan_and_route(
        total_miles=300, miles_to_pickup=50, speed=55
    )
    stops = _extract_stops(plan.segments, waypoints, route)

    start = next(s for s in stops if s["kind"] == "start")
    assert start["at"] == plan.segments[0].start.isoformat()
