from django.db import models
from djmoney.models.fields import MoneyField
from core.models import BaseModel


class Author(BaseModel):
    name = models.CharField(max_length=100)
    nationality = models.CharField(
        max_length=3,
        help_text="ISO 3166 ALPHA-3"
    )

    class Meta:
        ordering = ('name',)

    def __str__(self) -> str:
        return f'{self.pk} - {self.name}'


class BookManager(models.Manager):
    def contemporaries(self):
        return self.filter(year__gt=1950)

class Book(BaseModel):
    title = models.CharField(max_length=500)
    authors = models.ManyToManyField(
        'library.Author',
        related_name='books',
    )
    year = models.PositiveIntegerField(default=1900)
    language = models.CharField(
        max_length=2,
        default='es',
        help_text="ISO 639-1 Language",
    )
    cover_url = models.CharField(null=True, blank=True, max_length=500)
    price = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='MXN'
    )
    sellable = models.BooleanField(default=True)
    copies = models.PositiveIntegerField()
    description = models.TextField()

    objects = BookManager()

    def __str__(self) -> str:
        return f'{self.pk} - {self.title}'

    def in_stock(self) -> bool:
      return self.copies > 0
    
    def main_author(self) -> Author:
      return self.authors.first()


def run():
    for author in Author.objects.all():
        print(author.name, [book.title for book in author.books.all()])
    print('-' * 40)
    for book in Book.objects.all():
        print(book.title, [author.name for author in book.authors.all()])