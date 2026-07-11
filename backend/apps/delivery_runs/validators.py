from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_total_cash_collected(value) -> None:
    """Validate that total_cash_collected is not negative."""
    if value is not None and value < 0:
        raise ValidationError(_('Total cash collected cannot be negative.'))
