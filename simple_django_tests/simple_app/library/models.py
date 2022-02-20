from django.db import models
from django.db.models import manager


class Book(models.Model):
    title = models.CharField(max_length=500)
    year = models.IntegerField()

    def __str__(self):
        return f'({self.pk}) {self.title}'

class Author(models.Model):
    name = models.CharField(max_length=100)
    books = models.ManyToManyField(
        'library.Book',
        related_name='authors'
    )

    def __str__(self):
        return f'({self.pk}) {self.name}'
