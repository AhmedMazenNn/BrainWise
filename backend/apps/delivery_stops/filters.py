import django_filters

from .models import DeliveryStop


class DeliveryStopFilter(django_filters.FilterSet):
    class Meta:
        model = DeliveryStop
        fields = {
            'status': ['exact'],
            'delivery_run': ['exact'],
            'order': ['exact'],
        }
