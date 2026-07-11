from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class RoleChoices(models.TextChoices):
    MANAGER = 'MANAGER', 'Manager'
    DISPATCHER = 'DISPATCHER', 'Dispatcher'
    DRIVER = 'DRIVER', 'Driver'


class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.DRIVER,
    )

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'
