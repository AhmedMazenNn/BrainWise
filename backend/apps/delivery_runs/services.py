from django.db.models import QuerySet

from .models import DeliveryRun


def get_delivery_runs_for_driver(driver) -> QuerySet[DeliveryRun]:
    """Return all delivery runs for a specific driver."""
    return DeliveryRun.objects.filter(driver=driver)
