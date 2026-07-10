from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User

from .validators import validate_max_stops, validate_phone_number


class DriverStatus(models.TextChoices):
    AVAILABLE = 'AVAILABLE', _('Available')
    ON_RUN = 'ON_RUN', _('On Run')
    INACTIVE = 'INACTIVE', _('Inactive')


class Driver(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='driver_profile',
    )
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    active = models.BooleanField(default=True)
    max_stops_per_run = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=DriverStatus.choices,
        default=DriverStatus.AVAILABLE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Driver'
        verbose_name_plural = 'Drivers'

    def __str__(self) -> str:
        return f'{self.name} ({self.get_status_display()})'

    def clean(self) -> None:
        super().clean()
        validate_phone_number(self.phone_number)
        validate_max_stops(self.max_stops_per_run)
        if not self.active and self.status == DriverStatus.ON_RUN:
            raise ValidationError(
                _('A driver cannot be inactive while their status is ON_RUN.')
            )
        if self.status not in DriverStatus.values:
            raise ValidationError(
                _('Invalid status value: %(value)s.'),
                params={'value': self.status},
            )

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)
