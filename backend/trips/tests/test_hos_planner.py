"""Tests for the HOS planner.

These tests exercise the pure-python simulator with synthetic routes to make
sure the regulatory rules are honored.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trips.services.hos_planner import (
    CYCLE_LIMIT_HOURS,
    DROPOFF_HOURS,
    MAX_DRIVING_HOURS_PER_SHIFT,
    PICKUP_HOURS,
    REQUIRED_BREAK_HOURS,
    REQUIRED_REST_HOURS,
    Status,
    Waypoint,
    plan_trip,
)

DEPARTURE = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)


def _waypoints(miles_to_pickup: float, total: float) -> list[Waypoint]:
    return [
        Waypoint(miles_to_pickup, "Pickup", "pickup", PICKUP_HOURS, "P", 0.0, 0.0),
        Waypoint(total, "Dropoff", "dropoff", DROPOFF_HOURS, "D", 0.0, 0.0),
    ]


def _hours(segments, status: Status) -> float:
    return sum(s.hours for s in segments if s.status == status)


def test_short_trip_no_rest_required():
    """A 200-mile trip should complete in one shift without sleeper berth."""
    plan = plan_trip(
        departure=DEPARTURE,
        total_miles=200,
        average_speed_mph=50,
        current_cycle_used_hours=0,
        waypoints=_waypoints(50, 200),
    )
    assert not plan.needs_restart
    assert _hours(plan.segments, Status.SLEEPER) == 0
    # Pickup + dropoff = 2h on duty (not driving)
    assert _hours(plan.segments, Status.ON_DUTY) == pytest.approx(
        PICKUP_HOURS + DROPOFF_HOURS, rel=1e-3
    )
    # Driving should be ~4h (200 / 50)
    assert _hours(plan.segments, Status.DRIVING) == pytest.approx(4.0, rel=1e-3)


def test_long_trip_inserts_30_min_break_and_10h_rest():
    """A trip that exceeds 8h of driving must include a 30-min break, and >11h
    of driving must trigger a 10-h sleeper berth rest."""
    plan = plan_trip(
        departure=DEPARTURE,
        total_miles=800,   # ~14.5h of driving at 55 mph → needs rest + break
        average_speed_mph=55,
        current_cycle_used_hours=0,
        waypoints=_waypoints(100, 800),
    )
    # The planner must have inserted at least one 30-min break…
    breaks = [s for s in plan.segments if s.note == "30-minute break"]
    assert breaks, "Expected a 30-minute break for >8h of driving"
    # …and one 10-hour rest because 800 miles > 11h at 55 mph.
    rests = [s for s in plan.segments if s.status == Status.SLEEPER]
    assert rests, "Expected a 10-hour sleeper rest for >11h of driving"
    assert rests[0].hours == pytest.approx(REQUIRED_REST_HOURS)


def test_fuel_stop_inserted_every_1000_miles():
    plan = plan_trip(
        departure=DEPARTURE,
        total_miles=2200,
        average_speed_mph=55,
        current_cycle_used_hours=0,
        waypoints=_waypoints(50, 2200),
    )
    fuels = [s for s in plan.segments if s.note == "Fueling"]
    # 2200 miles → at least 2 fuel stops (one before 1000, one before 2000).
    assert len(fuels) >= 2


def test_driving_limit_never_exceeded_in_a_shift():
    """No individual shift (driving between two 10-h rests) exceeds 11h of
    driving or 14h of on-duty window."""
    plan = plan_trip(
        departure=DEPARTURE,
        total_miles=1500,
        average_speed_mph=55,
        current_cycle_used_hours=0,
        waypoints=_waypoints(50, 1500),
    )
    shifts: list[list] = [[]]
    for seg in plan.segments:
        if seg.status == Status.SLEEPER and seg.hours >= REQUIRED_REST_HOURS - 1e-6:
            shifts.append([])
        else:
            shifts[-1].append(seg)
    for shift in shifts:
        driving = sum(s.hours for s in shift if s.status == Status.DRIVING)
        window = sum(s.hours for s in shift)
        assert driving <= MAX_DRIVING_HOURS_PER_SHIFT + 1e-3
        assert window <= 14.0 + REQUIRED_BREAK_HOURS + 1e-3  # window + break window tolerance


def test_cycle_exhaustion_triggers_restart():
    """Starting with the cycle almost full forces a 34-h restart."""
    plan = plan_trip(
        departure=DEPARTURE,
        total_miles=1200,
        average_speed_mph=55,
        current_cycle_used_hours=CYCLE_LIMIT_HOURS - 5,
        waypoints=_waypoints(50, 1200),
    )
    assert any("restart" in s.note.lower() for s in plan.segments)
