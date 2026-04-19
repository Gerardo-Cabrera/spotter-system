"""Convert a list of HOS segments into Driver's Daily Log sheets.

Each log sheet corresponds to one calendar day in the driver's home-terminal
timezone. Segments are clipped at midnight so multi-day trips produce one log
per day, as required by the FMCSA guide."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone as _tz
from typing import Any
from zoneinfo import ZoneInfo

from .hos_planner import Segment, Status

STATUS_ROW = {
    Status.OFF_DUTY: 1,
    Status.SLEEPER: 2,
    Status.DRIVING: 3,
    Status.ON_DUTY: 4,
}


def build_daily_logs(
    segments: list[Segment],
    tz_name: str,
    *,
    driver_name: str = "",
    carrier_name: str = "",
    home_terminal: str = "",
) -> list[dict[str, Any]]:
    """Split segments by calendar day and format them for the ELD SVG renderer."""
    tz = ZoneInfo(tz_name) if tz_name else _tz.utc

    by_day: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for seg in segments:
        start_local = seg.start.astimezone(tz)
        end_local = seg.end.astimezone(tz)
        cursor = start_local
        while cursor < end_local:
            day = cursor.date()
            next_midnight = datetime.combine(day + timedelta(days=1), time.min, tz)
            chunk_end = min(end_local, next_midnight)
            by_day[day].append(
                {
                    "status": seg.status.value,
                    "status_row": STATUS_ROW[seg.status],
                    "start_hour": _to_hour_fraction(cursor),
                    "end_hour": _to_hour_fraction(chunk_end, day=day),
                    "start": cursor.isoformat(),
                    "end": chunk_end.isoformat(),
                    "note": seg.note,
                    "location_name": seg.location_name,
                    "miles": round(seg.miles * _chunk_ratio(seg, cursor, chunk_end), 2),
                }
            )
            cursor = chunk_end

    days_sorted = sorted(by_day.keys())
    logs: list[dict[str, Any]] = []
    for day in days_sorted:
        entries = by_day[day]
        totals = _totals(entries)
        logs.append(
            {
                "date": day.isoformat(),
                "timezone": tz_name,
                "driver_name": driver_name,
                "carrier_name": carrier_name,
                "home_terminal": home_terminal,
                "entries": entries,
                "totals_hours": totals,
                "total_miles_today": round(
                    sum(e["miles"] for e in entries if e["status"] == Status.DRIVING.value),
                    2,
                ),
            }
        )
    return logs


def _to_hour_fraction(dt: datetime, *, day: date | None = None) -> float:
    """Return the hour-of-day as a float in [0, 24].

    When a chunk ends exactly at midnight we return 24.0 so the log line can
    be drawn all the way to the right edge of the grid."""
    local_day = day or dt.date()
    start_of_day = datetime.combine(local_day, time.min, dt.tzinfo)
    hours = (dt - start_of_day).total_seconds() / 3600.0
    return max(0.0, min(24.0, hours))


def _chunk_ratio(seg: Segment, chunk_start: datetime, chunk_end: datetime) -> float:
    total = (seg.end - seg.start).total_seconds()
    if total <= 0:
        return 0.0
    return (chunk_end - chunk_start).total_seconds() / total


def _totals(entries: list[dict[str, Any]]) -> dict[str, float]:
    totals = {s.value: 0.0 for s in Status}
    for e in entries:
        totals[e["status"]] += max(0.0, e["end_hour"] - e["start_hour"])
    return {k: round(v, 2) for k, v in totals.items()}
