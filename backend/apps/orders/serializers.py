from rest_framework import serializers

from .models import Order
from .validators import PHONE_REGEX


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            'id',
            'customer_name',
            'customer_phone',
            'address',
            'cash_amount',
            'priority',
            'status',
            'assigned_driver',
            'created_at',
            'delivered_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_customer_name(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError('Customer name is required.')
        return value.strip()

    def validate_customer_phone(self, value: str) -> str:
        if value and not PHONE_REGEX.match(value.strip()):
            raise serializers.ValidationError(
                'Enter a valid phone number (e.g. +201234567890).'
            )
        return value.strip() if value else value

    def validate_address(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError('Address is required.')
        return value.strip()

    def validate_cash_amount(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Cash amount cannot be negative.')
        return value
