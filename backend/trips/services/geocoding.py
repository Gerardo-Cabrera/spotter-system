"""Geocoding client built on top of Nominatim (OpenStreetMap).

Nominatim is free, requires a polite User-Agent and rate-limits to ~1 rps.
We cache results aggressively in the Django cache to minimize requests."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60 * 60 * 24 * 7  # 1 week
REQUEST_TIMEOUT = 10


class GeocodingError(Exception):
    """Raised when a location cannot be geocoded."""


@dataclass
class GeocodeResult:
    query: str
    display_name: str
    latitude: float
    longitude: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "display_name": self.display_name,
            "lat": self.latitude,
            "lon": self.longitude,
        }


def geocode(query: str) -> GeocodeResult:
    """Resolve a free-text location into lat/lon via Nominatim."""
    query = (query or "").strip()
    if not query:
        raise GeocodingError("Empty location query.")

    cache_key = f"geocode:{query.lower()}"
    cached = cache.get(cache_key)
    if cached:
        return GeocodeResult(**cached)

    url = f"{settings.NOMINATIM_BASE_URL.rstrip('/')}/search"
    headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}
    params = {"q": query, "format": "json", "limit": 1, "addressdetails": 0}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:  # pragma: no cover - network
        logger.exception("Nominatim request failed")
        raise GeocodingError(f"Geocoding service error: {exc}") from exc

    if not payload:
        raise GeocodingError(f"Could not geocode '{query}'.")

    first = payload[0]
    result = GeocodeResult(
        query=query,
        display_name=first.get("display_name", query),
        latitude=float(first["lat"]),
        longitude=float(first["lon"]),
    )
    cache.set(cache_key, result.__dict__, CACHE_TTL_SECONDS)
    return result


def autocomplete(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return a list of matching suggestions for a partial query."""
    query = (query or "").strip()
    if len(query) < 3:
        return []

    cache_key = f"autocomplete:{query.lower()}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"{settings.NOMINATIM_BASE_URL.rstrip('/')}/search"
    headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}
    params = {"q": query, "format": "json", "limit": limit, "addressdetails": 0}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:  # pragma: no cover - network
        return []

    suggestions = [
        {
            "display_name": item.get("display_name", ""),
            "lat": float(item["lat"]),
            "lon": float(item["lon"]),
        }
        for item in payload
    ]
    cache.set(cache_key, suggestions, 60 * 60)
    return suggestions
