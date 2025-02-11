from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager as AbstractUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(AbstractUserManager):
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


class UserFollowing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'following',)

    def __str__(self):
        return f"{self.user.username} follows {self.following.username}"

    def save(self, *args, **kwargs):
        # Avoid circular following
        if self.user == self.following:
            raise ValueError("User can not follow itself")
        super().save(*args, **kwargs)
