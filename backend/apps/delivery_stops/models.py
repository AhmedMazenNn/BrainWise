from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .validators import validate_cash_amount, validate_stop_sequence


class StopStatus(models.TextChoices):
    ASSIGNED = 'ASSIGNED', _('Assigned')
    EN_ROUTE = 'EN_ROUTE', _('En Route')
    DELIVERED = 'DELIVERED', _('Delivered')
    FAILED = 'FAILED', _('Failed')


class DeliveryStop(models.Model):
    delivery_run = models.ForeignKey(
        'delivery_runs.DeliveryRun',
        on_delete=models.CASCADE,
        related_name='stops',
    )
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='delivery_stop',
    )
    stop_sequence = models.PositiveIntegerField()
    customer_name = models.CharField(max_length=255)
    address = models.TextField()
    cash_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=StopStatus.choices,
        default=StopStatus.ASSIGNED,
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['stop_sequence']
        verbose_name = 'Delivery Stop'
        verbose_name_plural = 'Delivery Stops'
        indexes = [
            models.Index(fields=['delivery_run']),
            models.Index(fields=['order']),
            models.Index(fields=['status']),
            models.Index(fields=['stop_sequence']),
        ]

    def __str__(self) -> str:
        return (
            f'Stop #{self.stop_sequence} - {self.customer_name} '
            f'({self.get_status_display()})'
        )

    def clean(self) -> None:
        super().clean()
        validate_stop_sequence(self.stop_sequence)
        validate_cash_amount(self.cash_amount)
        if self.status not in StopStatus.values:
            raise ValidationError(
                _('Invalid status value: %(value)s.'),
                params={'value': self.status},
            )

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)
