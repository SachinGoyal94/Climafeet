from datetime import UTC, datetime, timedelta

from rest_framework import serializers

MAX_DAYS_AHEAD = 7


class PlaceSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=200, required=False, allow_blank=True)
    lat = serializers.FloatField(min_value=-90, max_value=90, required=False, allow_null=True)
    lon = serializers.FloatField(min_value=-180, max_value=180, required=False, allow_null=True)

    def validate(self, attrs):
        has_coords = attrs.get("lat") is not None and attrs.get("lon") is not None
        if not has_coords and not attrs.get("label", "").strip():
            raise serializers.ValidationError("Enter a place name or pick a suggestion.")
        return attrs


class PlanRequestSerializer(serializers.Serializer):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure = serializers.DateTimeField()
    load_lb = serializers.FloatField(min_value=0, max_value=100_000)
    interval_miles = serializers.ChoiceField(choices=[10, 25, 50], default=25)

    def validate_departure(self, value):
        now = datetime.now(UTC)
        if value < now - timedelta(hours=1):
            raise serializers.ValidationError("Departure is in the past.")
        if value > now + timedelta(days=MAX_DAYS_AHEAD):
            raise serializers.ValidationError(
                f"Departure must be within {MAX_DAYS_AHEAD} days so the forecast covers the trip."
            )
        return value
