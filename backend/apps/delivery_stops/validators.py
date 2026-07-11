from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_stop_sequence(value) -> None:
    """Validate that stop_sequence is greater than zero."""
    if value is None or value < 1:
        raise ValidationError(_('stop_sequence must be greater than zero.'))


def validate_cash_amount(value) -> None:
    """Validate that cash_amount is not negative."""
    if value is not None and value < 0:
        raise ValidationError(_('Cash amount cannot be negative.'))
