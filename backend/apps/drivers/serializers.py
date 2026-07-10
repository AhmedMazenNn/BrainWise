from rest_framework import serializers

from .models import Driver, DriverStatus


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = [
            'id',
            'user',
            'name',
            'phone_number',
            'active',
            'max_stops_per_run',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_phone_number(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError('Phone number is required.')
        return value.strip()

    def validate_max_stops_per_run(self, value: int) -> int:
        if value is None or value < 1:
            raise serializers.ValidationError('max_stops_per_run must be at least 1.')
        return value

    def validate_status(self, value: str) -> str:
        if value not in DriverStatus.values:
            raise serializers.ValidationError(
                f'Invalid status. Allowed values: {", ".join(DriverStatus.values)}.'
            )
        return value

    def validate(self, attrs):
        active = attrs.get('active', getattr(self.instance, 'active', True))
        status = attrs.get('status', getattr(self.instance, 'status', DriverStatus.AVAILABLE))
        if not active and status == DriverStatus.ON_RUN:
            raise serializers.ValidationError(
                {'status': 'A driver cannot be inactive while their status is ON_RUN.'}
            )
        return attrs
