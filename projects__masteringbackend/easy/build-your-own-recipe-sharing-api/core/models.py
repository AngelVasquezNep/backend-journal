from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def get_system_user(self):
        system_user, created = User.objects.get_or_create(
            username='system',
            is_staff=True,
            is_superuser=True,
            is_active=True,
            email='system@system.com')
        return system_user


class User(AbstractUser):
    first_name = models.CharField(_("first name"), max_length=150, blank=True, null=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True, null=True)
    email = models.EmailField(_("email address"), unique=True)

    objects = UserManager()
