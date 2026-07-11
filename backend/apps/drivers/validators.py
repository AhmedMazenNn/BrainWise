import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

PHONE_REGEX = re.compile(r'^\+?[\d\s\-()]{7,20}$')


def validate_phone_number(value: str) -> None:
    """Validate that phone number is non-empty and matches a reasonable format."""
    if not value or not value.strip():
        raise ValidationError(_('Phone number is required.'))
    if not PHONE_REGEX.match(value.strip()):
        raise ValidationError(
            _('Enter a valid phone number (7-20 digits, may include +, spaces, dashes, parentheses).')
        )


def validate_max_stops(value: int) -> None:
    """Validate that max_stops_per_run is at least 1."""
    if value is None or value < 1:
        raise ValidationError(_('max_stops_per_run must be at least 1.'))
