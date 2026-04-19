"""Trip persistence — optional. The planner is fully stateless; these models
let clients save a computed plan for later retrieval by UUID."""
from __future__ import annotations

import uuid

from django.db import models


class Trip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Inputs
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    current_cycle_used_hours = models.FloatField()
    departure_time = models.DateTimeField()

    # Computed outputs (stored as JSON for simplicity)
    timezone = models.CharField(max_length=64)
    total_miles = models.FloatField()
    total_driving_hours = models.FloatField()
    total_on_duty_hours = models.FloatField()
    total_days = models.IntegerField()

    route_geometry = models.JSONField()  # list[[lat, lon]]
    stops = models.JSONField()           # list[dict]
    segments = models.JSONField()        # full HOS timeline
    daily_logs = models.JSONField()      # one entry per calendar day
    geocoded = models.JSONField()        # resolved coordinates for inputs

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Trip {self.id} ({self.current_location} → {self.dropoff_location})"
