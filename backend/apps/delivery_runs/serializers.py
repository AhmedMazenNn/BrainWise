from rest_framework import serializers

from .models import DeliveryRun


class DeliveryRunSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.name', read_only=True)

    class Meta:
        model = DeliveryRun
        fields = [
            'id',
            'driver',
            'driver_name',
            'status',
            'total_cash_collected',
            'started_at',
            'completed_at',
            'cash_banked_at',
            'cash_banked_location',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_total_cash_collected(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Total cash collected cannot be negative.')
        return value
