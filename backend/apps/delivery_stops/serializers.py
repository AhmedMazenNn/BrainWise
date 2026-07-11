from rest_framework import serializers

from .models import DeliveryStop


class DeliveryStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryStop
        fields = [
            'id',
            'delivery_run',
            'order',
            'stop_sequence',
            'customer_name',
            'address',
            'cash_amount',
            'status',
            'delivered_at',
            'failed_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'customer_name', 'address', 'cash_amount',
            'created_at', 'updated_at',
        ]

    def validate_stop_sequence(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError('stop_sequence must be greater than zero.')
        return value

    def validate_cash_amount(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Cash amount cannot be negative.')
        return value
