from django.contrib import admin

from .models import Trip


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "current_location",
        "pickup_location",
        "dropoff_location",
        "total_miles",
        "total_days",
        "created_at",
    )
    readonly_fields = tuple(f.name for f in Trip._meta.fields)
