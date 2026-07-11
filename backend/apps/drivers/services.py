from django.db.models import QuerySet

from .models import Driver, DriverStatus


def get_available_drivers() -> QuerySet[Driver]:
    """Return all active drivers with AVAILABLE status."""
    return Driver.objects.select_related('user').filter(
        active=True,
        status=DriverStatus.AVAILABLE,
    )
