from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.drivers.models import Driver

from .validators import validate_address, validate_cash_amount, validate_customer_name


class OrderPriority(models.TextChoices):
    HIGH = 'HIGH', _('High')
    MEDIUM = 'MEDIUM', _('Medium')
    LOW = 'LOW', _('Low')


class OrderStatus(models.TextChoices):
    OPEN = 'OPEN', _('Open')
    ASSIGNED = 'ASSIGNED', _('Assigned')
    EN_ROUTE = 'EN_ROUTE', _('En Route')
    DELIVERED = 'DELIVERED', _('Delivered')
    FAILED = 'FAILED', _('Failed')
    CASH_BANKED = 'CASH_BANKED', _('Cash Banked')


class Order(models.Model):
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField()
    cash_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    priority = models.CharField(
        max_length=10,
        choices=OrderPriority.choices,
        default=OrderPriority.MEDIUM,
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.OPEN,
    )
    assigned_driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )
    # TODO: Add delivery_run ForeignKey when the Delivery Runs app is implemented.
    # Expected: models.ForeignKey('delivery_runs.DeliveryRun', on_delete=models.SET_NULL,
    #           null=True, blank=True, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['assigned_driver']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self) -> str:
        return f'Order #{self.pk} - {self.customer_name} ({self.get_status_display()})'

    def clean(self) -> None:
        super().clean()
        validate_customer_name(self.customer_name)
        validate_address(self.address)
        validate_cash_amount(self.cash_amount)
        if self.status not in OrderStatus.values:
            raise ValidationError(
                _('Invalid status value: %(value)s.'),
                params={'value': self.status},
            )
        if self.priority not in OrderPriority.values:
            raise ValidationError(
                _('Invalid priority value: %(value)s.'),
                params={'value': self.priority},
            )

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)
