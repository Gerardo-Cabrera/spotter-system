from rest_framework import serializers

from .models import Trip


class TripInputSerializer(serializers.Serializer):
    current_location = serializers.CharField(max_length=255)
    pickup_location = serializers.CharField(max_length=255)
    dropoff_location = serializers.CharField(max_length=255)
    current_cycle_used_hours = serializers.FloatField(min_value=0, max_value=70)
    departure_time = serializers.DateTimeField(required=False, allow_null=True)
    driver_name = serializers.CharField(required=False, allow_blank=True, default="")
    carrier_name = serializers.CharField(required=False, allow_blank=True, default="")
    save = serializers.BooleanField(required=False, default=False)


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = "__all__"
