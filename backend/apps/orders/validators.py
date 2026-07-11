from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_customer_name(value: str) -> None:
    """Validate that customer_name is non-empty."""
    if not value or not value.strip():
        raise ValidationError(_('Customer name is required.'))


def validate_address(value: str) -> None:
    """Validate that address is non-empty."""
    if not value or not value.strip():
        raise ValidationError(_('Address is required.'))


def validate_cash_amount(value) -> None:
    """Validate that cash_amount is not negative."""
    if value is not None and value < 0:
        raise ValidationError(_('Cash amount cannot be negative.'))
