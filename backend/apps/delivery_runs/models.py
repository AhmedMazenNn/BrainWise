from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .validators import validate_total_cash_collected


class RunStatus(models.TextChoices):
    DRAFT = 'DRAFT', _('Draft')
    ASSIGNED = 'ASSIGNED', _('Assigned')
    EN_ROUTE = 'EN_ROUTE', _('En Route')
    COMPLETED = 'COMPLETED', _('Completed')
    CASH_BANKED = 'CASH_BANKED', _('Cash Banked')
    CANCELLED = 'CANCELLED', _('Cancelled')


class DeliveryRun(models.Model):
    driver = models.ForeignKey(
        'drivers.Driver',
        on_delete=models.PROTECT,
        related_name='delivery_runs',
    )
    status = models.CharField(
        max_length=20,
        choices=RunStatus.choices,
        default=RunStatus.DRAFT,
    )
    total_cash_collected = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cash_banked_at = models.DateTimeField(null=True, blank=True)
    cash_banked_location = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Delivery Run'
        verbose_name_plural = 'Delivery Runs'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['driver']),
            models.Index(fields=['created_at']),
            models.Index(fields=['started_at']),
        ]

    def __str__(self) -> str:
        return f'DeliveryRun #{self.pk} - {self.driver.name} ({self.get_status_display()})'

    @property
    def stops_count(self) -> int:
        """Return the number of stops for this run.

        Placeholder for DeliveryStop integration.
        TODO: Replace with self.stops.count() when DeliveryStop model is implemented.
        """
        return 0

    def clean(self) -> None:
        super().clean()
        validate_total_cash_collected(self.total_cash_collected)
        if self.status not in RunStatus.values:
            raise ValidationError(
                _('Invalid status value: %(value)s.'),
                params={'value': self.status},
            )
        if self.cash_banked_location and not self.cash_banked_at:
            raise ValidationError(
                _('cash_banked_at is required when cash_banked_location is provided.')
            )

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)
