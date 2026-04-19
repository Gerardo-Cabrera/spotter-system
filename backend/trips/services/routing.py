"""Routing service.

Primary provider: public OSRM demo server (free, no key).
Fallback: OpenRouteService (free tier, ~2000 requests/day) when an API key is
configured and OSRM fails. The result is normalized regardless of provider."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20
METERS_TO_MILES = 0.000621371
CACHE_TTL_SECONDS = 60 * 60 * 24  # 1 day


class RoutingError(Exception):
    """Raised when no routing provider can produce a route."""


@dataclass
class RouteLeg:
    start: tuple[float, float]
    end: tuple[float, float]
    distance_miles: float
    duration_hours: float
    geometry: list[list[float]]  # list of [lat, lon] points


@dataclass
class Route:
    legs: list[RouteLeg]

    @property
    def total_miles(self) -> float:
        return sum(leg.distance_miles for leg in self.legs)

    @property
    def total_hours(self) -> float:
        return sum(leg.duration_hours for leg in self.legs)

    @property
    def geometry(self) -> list[list[float]]:
        merged: list[list[float]] = []
        for i, leg in enumerate(self.legs):
            points = leg.geometry if i == 0 else leg.geometry[1:]
            merged.extend(points)
        return merged


def route_through(points: list[tuple[float, float]]) -> Route:
    """Build a route traversing the given ordered points (lat, lon)."""
    if len(points) < 2:
        raise RoutingError("At least two points are required to build a route.")

    legs: list[RouteLeg] = []
    for start, end in zip(points, points[1:]):
        legs.append(_route_leg(start, end))
    return Route(legs=legs)


def _route_leg(start: tuple[float, float], end: tuple[float, float]) -> RouteLeg:
    cache_key = f"route:{start[0]:.5f},{start[1]:.5f}->{end[0]:.5f},{end[1]:.5f}"
    cached = cache.get(cache_key)
    if cached:
        return RouteLeg(**cached)

    errors: list[str] = []
    try:
        leg = _osrm_leg(start, end)
    except RoutingError as exc:
        errors.append(f"osrm: {exc}")
        leg = None

    if leg is None and settings.ORS_API_KEY:
        try:
            leg = _ors_leg(start, end)
        except RoutingError as exc:
            errors.append(f"ors: {exc}")

    if leg is None:
        raise RoutingError(
            "All routing providers failed: " + "; ".join(errors) if errors else "unknown error"
        )

    cache.set(cache_key, leg.__dict__, CACHE_TTL_SECONDS)
    return leg


def _osrm_leg(start: tuple[float, float], end: tuple[float, float]) -> RouteLeg:
    base = settings.OSRM_BASE_URL.rstrip("/")
    coords = f"{start[1]},{start[0]};{end[1]},{end[0]}"
    url = f"{base}/route/v1/driving/{coords}"
    params = {"overview": "full", "geometries": "geojson"}
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise RoutingError(str(exc)) from exc

    if data.get("code") != "Ok" or not data.get("routes"):
        raise RoutingError(data.get("message", "no route"))

    best: dict[str, Any] = data["routes"][0]
    geom = best["geometry"]["coordinates"]  # [lon, lat]
    return RouteLeg(
        start=start,
        end=end,
        distance_miles=best["distance"] * METERS_TO_MILES,
        duration_hours=best["duration"] / 3600.0,
        geometry=[[lat, lon] for lon, lat in geom],
    )


def _ors_leg(start: tuple[float, float], end: tuple[float, float]) -> RouteLeg:
    base = settings.ORS_BASE_URL.rstrip("/")
    url = f"{base}/v2/directions/driving-hgv/geojson"
    headers = {
        "Authorization": settings.ORS_API_KEY,
        "Content-Type": "application/json",
    }
    body = {"coordinates": [[start[1], start[0]], [end[1], end[0]]]}
    try:
        response = requests.post(url, json=body, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise RoutingError(str(exc)) from exc

    feature = (data.get("features") or [None])[0]
    if not feature:
        raise RoutingError("no route from ORS")

    summary = feature["properties"]["summary"]
    geom = feature["geometry"]["coordinates"]
    return RouteLeg(
        start=start,
        end=end,
        distance_miles=summary["distance"] * METERS_TO_MILES,
        duration_hours=summary["duration"] / 3600.0,
        geometry=[[lat, lon] for lon, lat in geom],
    )
