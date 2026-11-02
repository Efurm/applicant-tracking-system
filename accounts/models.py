from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    STAFF = "staff", "Staff"


class AccountManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """A hiring-team employee. The role decides what they may do in the app.

    The role drives Django's own flags: Admins get ``is_staff`` and
    ``is_superuser`` so they can manage users in /admin/; Staff get neither.
    Users are deactivated with ``is_active`` rather than deleted.
    """

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STAFF)

    objects = AccountManager()

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    def save(self, *args, **kwargs):
        self.is_staff = self.is_superuser = self.is_admin
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username
