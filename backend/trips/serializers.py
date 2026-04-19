from rest_framework import serializers

from .models import Trip


class TripInputSerializer(serializers.Serializer):
    """Payload accepted by `POST /api/trips/plan/`."""

    current_location = serializers.CharField(
        max_length=255,
        help_text="Free-text current location of the driver (geocoded via Nominatim).",
    )
    pickup_location = serializers.CharField(
        max_length=255,
        help_text="Free-text pickup address. Also determines the driver's home timezone.",
    )
    dropoff_location = serializers.CharField(
        max_length=255,
        help_text="Free-text dropoff address.",
    )
    current_cycle_used_hours = serializers.FloatField(
        min_value=0,
        max_value=70,
        help_text="Hours already consumed in the current 70h/8-day cycle (0–70).",
    )
    departure_time = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="ISO-8601 departure timestamp. Defaults to the current UTC time.",
    )
    driver_name = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional driver name, shown on the rendered log sheets.",
    )
    carrier_name = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional carrier name, shown on the rendered log sheets.",
    )
    save = serializers.BooleanField(
        required=False,
        default=False,
        help_text="When true, persist the computed plan and return a `trip_id`.",
    )


class GeocodeResultSerializer(serializers.Serializer):
    """Single autocomplete suggestion returned by `/api/geocode/`."""

    display_name = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()


class GeocodeResponseSerializer(serializers.Serializer):
    results = GeocodeResultSerializer(many=True)


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = "__all__"
