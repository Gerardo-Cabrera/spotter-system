"""Hours of Service (HOS) planner for property-carrying drivers (70h / 8-day).

Implements the rules relevant to this assessment:

* 11-hour driving limit after 10 consecutive hours off-duty.
* 14-hour on-duty window after coming on duty following 10 hours off.
* 30-minute break required after 8 cumulative hours of driving without a
  break of at least 30 minutes (off-duty or sleeper berth).
* 70-hour / 8-day on-duty limit (rolling; we approximate by summing on-duty
  time during the trip on top of the cycle hours the driver declared).
* 10 consecutive hours off-duty resets the driving/window counters.
* Pickup and drop-off consume 1 hour on-duty (not driving).
* Fueling consumes 15 minutes on-duty (not driving) at least every 1000 miles.

The planner is a **pure function**: given the trip inputs it returns a list of
segments plus a summary. It does not hit the network or the database.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Iterable


class Status(str, Enum):
    OFF_DUTY = "off_duty"
    SLEEPER = "sleeper"
    DRIVING = "driving"
    ON_DUTY = "on_duty"  # on-duty not driving


# Regulatory constants
MAX_DRIVING_HOURS_PER_SHIFT = 11.0
MAX_WINDOW_HOURS = 14.0
MAX_DRIVING_BEFORE_BREAK_HOURS = 8.0
REQUIRED_BREAK_HOURS = 0.5
REQUIRED_REST_HOURS = 10.0
CYCLE_LIMIT_HOURS = 70.0
MAX_MILES_BETWEEN_FUEL = 1000.0
PICKUP_HOURS = 1.0
DROPOFF_HOURS = 1.0
FUEL_HOURS = 0.25
RESTART_HOURS = 34.0


@dataclass
class Waypoint:
    """A mandatory stop along the route with its position in miles from start."""

    miles_from_start: float
    label: str           # "Pickup" / "Dropoff"
    kind: str            # "pickup" / "dropoff"
    on_duty_hours: float
    location_name: str
    lat: float
    lon: float


@dataclass
class Segment:
    status: Status
    start: datetime
    end: datetime
    miles: float
    note: str
    location_name: str
    lat: float
    lon: float

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "hours": round(self.hours, 4),
            "miles": round(self.miles, 2),
            "note": self.note,
            "location_name": self.location_name,
            "lat": self.lat,
            "lon": self.lon,
        }


@dataclass
class PlanResult:
    segments: list[Segment]
    total_miles: float
    total_driving_hours: float
    total_on_duty_hours: float
    cycle_used_hours_end: float
    needs_restart: bool

    def to_dict(self) -> dict:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "total_miles": round(self.total_miles, 2),
            "total_driving_hours": round(self.total_driving_hours, 2),
            "total_on_duty_hours": round(self.total_on_duty_hours, 2),
            "cycle_used_hours_end": round(self.cycle_used_hours_end, 2),
            "needs_restart": self.needs_restart,
        }


@dataclass
class _State:
    clock: datetime
    miles_done: float = 0.0
    cycle_used: float = 0.0
    driving_today: float = 0.0
    window_elapsed: float = 0.0
    driving_since_break: float = 0.0
    miles_since_fuel: float = 0.0
    on_duty: bool = False  # has the 14-h window started?
    segments: list[Segment] = field(default_factory=list)


def plan_trip(
    *,
    departure: datetime,
    total_miles: float,
    average_speed_mph: float,
    current_cycle_used_hours: float,
    waypoints: Iterable[Waypoint],
    route_geometry: list[list[float]] | None = None,
) -> PlanResult:
    """Simulate a trip applying HOS rules.

    Args:
        departure: Start datetime (timezone-aware).
        total_miles: Total driving distance in miles.
        average_speed_mph: Effective average speed produced by the router.
        current_cycle_used_hours: Hours already used in the rolling 70h/8d cycle
            when the driver starts the trip.
        waypoints: Ordered mandatory stops (pickup + dropoff). Their
            ``miles_from_start`` should be strictly increasing and the last one
            must equal ``total_miles``.
    """
    if average_speed_mph <= 0:
        raise ValueError("average_speed_mph must be positive.")
    if total_miles <= 0:
        raise ValueError("total_miles must be positive.")

    route_geometry = route_geometry or []
    waypoints = sorted(waypoints, key=lambda w: w.miles_from_start)
    if not waypoints or waypoints[-1].miles_from_start < total_miles - 1e-6:
        raise ValueError("Waypoints must end at total_miles (dropoff).")

    state = _State(clock=departure, cycle_used=current_cycle_used_hours)
    waypoint_idx = 0

    def _loc_at(miles: float) -> tuple[float, float]:
        if not route_geometry:
            return (0.0, 0.0)
        if miles <= 0:
            return tuple(route_geometry[0])  # type: ignore[return-value]
        if miles >= total_miles:
            return tuple(route_geometry[-1])  # type: ignore[return-value]
        ratio = miles / total_miles
        idx = min(int(ratio * (len(route_geometry) - 1)), len(route_geometry) - 1)
        return tuple(route_geometry[idx])  # type: ignore[return-value]

    def _append(status: Status, hours: float, *, miles: float, note: str, loc: str) -> None:
        if hours <= 0:
            return
        start = state.clock
        end = start + timedelta(hours=hours)
        lat, lon = _loc_at(state.miles_done)
        state.segments.append(
            Segment(
                status=status,
                start=start,
                end=end,
                miles=miles,
                note=note,
                location_name=loc,
                lat=lat,
                lon=lon,
            )
        )
        state.clock = end
        if status == Status.DRIVING:
            state.driving_today += hours
            state.driving_since_break += hours
            state.window_elapsed += hours
            state.cycle_used += hours
            state.miles_done += miles
            state.miles_since_fuel += miles
            state.on_duty = True
        elif status == Status.ON_DUTY:
            state.window_elapsed += hours
            state.cycle_used += hours
            state.on_duty = True
        elif status in (Status.OFF_DUTY, Status.SLEEPER):
            # A qualifying break (>=30 min) resets the 8-hour break counter.
            if hours >= REQUIRED_BREAK_HOURS:
                state.driving_since_break = 0.0
            # A full 10-hour rest restarts the shift window.
            if hours >= REQUIRED_REST_HOURS:
                state.driving_today = 0.0
                state.window_elapsed = 0.0
                state.on_duty = False

    def _rest_10h(loc: str) -> None:
        _append(Status.SLEEPER, REQUIRED_REST_HOURS, miles=0.0, note="10h rest", loc=loc)

    # ──────────────────────────────────────────────────────────────────────────
    # Main simulation loop
    # ──────────────────────────────────────────────────────────────────────────
    while waypoint_idx < len(waypoints):
        wp = waypoints[waypoint_idx]
        miles_to_wp = wp.miles_from_start - state.miles_done

        if miles_to_wp <= 1e-6:
            # We have reached this waypoint — perform its on-duty activity.
            _append(
                Status.ON_DUTY,
                wp.on_duty_hours,
                miles=0.0,
                note=f"{wp.label}",
                loc=wp.location_name,
            )
            waypoint_idx += 1
            continue

        prev_label = waypoints[waypoint_idx - 1].label if waypoint_idx > 0 else "Start"
        en_route_label = f"En route ({prev_label} → {wp.label}) — mile {int(state.miles_done)}"

        # Cycle exhausted — force 34h restart.
        if state.cycle_used >= CYCLE_LIMIT_HOURS - 1e-6:
            _append(
                Status.OFF_DUTY,
                RESTART_HOURS,
                miles=0.0,
                note="34h restart (70h cycle reached)",
                loc=en_route_label,
            )
            state.cycle_used = 0.0
            state.driving_today = 0.0
            state.window_elapsed = 0.0
            state.driving_since_break = 0.0
            continue

        # Mandatory 10-hour rest when the shift caps are reached.
        shift_driving_remaining = MAX_DRIVING_HOURS_PER_SHIFT - state.driving_today
        shift_window_remaining = MAX_WINDOW_HOURS - state.window_elapsed
        if shift_driving_remaining <= 1e-6 or shift_window_remaining <= 1e-6:
            _rest_10h(en_route_label)
            continue

        # Mandatory 30-minute break.
        break_remaining = MAX_DRIVING_BEFORE_BREAK_HOURS - state.driving_since_break
        if break_remaining <= 1e-6:
            _append(
                Status.OFF_DUTY,
                REQUIRED_BREAK_HOURS,
                miles=0.0,
                note="30-minute break",
                loc=en_route_label,
            )
            continue

        # Fueling every 1000 miles.
        fuel_remaining_miles = MAX_MILES_BETWEEN_FUEL - state.miles_since_fuel
        if fuel_remaining_miles <= 1e-6:
            _append(
                Status.ON_DUTY,
                FUEL_HOURS,
                miles=0.0,
                note="Fueling",
                loc=en_route_label,
            )
            state.miles_since_fuel = 0.0
            continue

        # Compute how far we can drive before hitting the next constraint.
        hours_cap = min(
            shift_driving_remaining,
            shift_window_remaining,
            break_remaining,
            CYCLE_LIMIT_HOURS - state.cycle_used,
        )
        miles_cap_hours = min(hours_cap, fuel_remaining_miles / average_speed_mph)
        miles_cap_hours = min(miles_cap_hours, miles_to_wp / average_speed_mph)

        if miles_cap_hours <= 1e-6:
            # Defensive: avoid infinite loops.
            break

        drive_hours = miles_cap_hours
        drive_miles = drive_hours * average_speed_mph
        _append(
            Status.DRIVING,
            drive_hours,
            miles=drive_miles,
            note=f"Driving toward {wp.label}",
            loc=en_route_label,
        )

    total_driving = sum(s.hours for s in state.segments if s.status == Status.DRIVING)
    total_on_duty = sum(
        s.hours for s in state.segments if s.status in (Status.DRIVING, Status.ON_DUTY)
    )

    return PlanResult(
        segments=state.segments,
        total_miles=state.miles_done,
        total_driving_hours=total_driving,
        total_on_duty_hours=total_on_duty,
        cycle_used_hours_end=state.cycle_used,
        needs_restart=state.cycle_used >= CYCLE_LIMIT_HOURS - 1e-6,
    )


