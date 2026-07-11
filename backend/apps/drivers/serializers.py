import re

from rest_framework import serializers

from apps.accounts.serializers import UserCreateSerializer

from .models import Driver, DriverStatus

PHONE_REGEX = re.compile(r'^\+?[\d\s\-()]{7,20}$')


class DriverSerializer(serializers.ModelSerializer):
    user_data = UserCreateSerializer(write_only=True, required=False)

    class Meta:
        model = Driver
        fields = [
            'id',
            'user',
            'user_data',
            'name',
            'phone_number',
            'active',
            'max_stops_per_run',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {'user': {'required': False}}

    def validate_name(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError('Driver name is required.')
        return value.strip()

    def validate_phone_number(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError('Phone number is required.')
        value = value.strip()
        if not PHONE_REGEX.match(value):
            raise serializers.ValidationError(
                'Enter a valid phone number (e.g. +201234567890).'
            )
        return value

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
        if self.instance is None and 'user_data' not in attrs and 'user' not in attrs:
            raise serializers.ValidationError(
                {'user_data': 'Provide user_data to create a new driver account.'}
            )
        active = attrs.get('active', getattr(self.instance, 'active', True))
        status = attrs.get('status', getattr(self.instance, 'status', DriverStatus.AVAILABLE))
        if not active and status == DriverStatus.ON_RUN:
            raise serializers.ValidationError(
                {'status': 'A driver cannot be inactive while their status is ON_RUN.'}
            )
        return attrs

    def create(self, validated_data):
        user_data = validated_data.pop('user_data', None)
        if user_data:
            user_serializer = UserCreateSerializer(data=user_data)
            user_serializer.is_valid(raise_exception=True)
            user = user_serializer.save()
            validated_data['user'] = user
        return super().create(validated_data)
