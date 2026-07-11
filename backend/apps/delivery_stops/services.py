from django.db.models import QuerySet

from .models import DeliveryStop


def get_stops_for_delivery_run(delivery_run) -> QuerySet[DeliveryStop]:
    """Return all stops for a specific delivery run, ordered by sequence."""
    return DeliveryStop.objects.filter(delivery_run=delivery_run).order_by('stop_sequence')


def get_stops_for_driver(driver) -> QuerySet[DeliveryStop]:
    """Return all stops assigned to a driver through their delivery runs."""
    return DeliveryStop.objects.filter(
        delivery_run__driver=driver,
    ).select_related('delivery_run', 'order').order_by('stop_sequence')
