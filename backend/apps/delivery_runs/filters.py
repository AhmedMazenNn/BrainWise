import django_filters

from .models import DeliveryRun


class DeliveryRunFilter(django_filters.FilterSet):
    class Meta:
        model = DeliveryRun
        fields = {
            'status': ['exact'],
            'driver': ['exact'],
        }
