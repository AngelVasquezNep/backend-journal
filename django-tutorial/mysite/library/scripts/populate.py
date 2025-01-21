from library.models import (BookGenre, Genre, Lang, Author, Book)

def populate():
    Genre.objects.all().delete()
    for genre in BookGenre:
        Genre.objects.create(name=genre)

    for language in Lang.LangChoices:
        Lang.objects.create(name=language)

    angel = Author.objects.create(full_name="Angel")
    dani = Author.objects.create(full_name="Dani")

    
