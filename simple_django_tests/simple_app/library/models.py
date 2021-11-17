from django.db import models

from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=500)
    year = models.IntegerField()
    authors = models.ManyToManyField(
        'library.Author',
        related_name='books'
    )


    def __str__(self) -> str:
        return self.title


class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.name
