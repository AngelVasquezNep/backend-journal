from django.db import models
from django.db.models import manager


class Books(models.Model):
    title = models.CharField(max_length=500)
    year = models.IntegerField()

    def __str__(self):
        return f'{self.title} ({self.pk})'

# Authors.objects.from_this_year()
# -> Authors.objects.filter(year=2021)

# class AuthorsManager(models.Manager):
#     def from_this_year(self):
#         self.filter(year=2021)

class Authors(models.Model):
    name = models.CharField(max_length=100)
    book = models.ForeignKey(
        'library.Books',
        on_delete=models.CASCADE,
        related_name='authors'
    )

    # manager = AuthorsManager()