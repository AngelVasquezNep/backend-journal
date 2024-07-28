import os
import json
from library.models import Author, Book

current_dir = os.path.dirname(__file__)


def json_to_dict(file_path):
    with open(os.path.join(current_dir, file_path), 'r') as file:
        return json.load(file)


def populate():
    authors = json_to_dict('./authors.json')
    books = json_to_dict('./books.json')

    Author.all_objects.all().hard_delete()
    Book.all_objects.all().hard_delete()

    for author in authors:
        Author.objects.create(**author)

    all_authors = list(Author.objects.all())

    for raw_book in books:
        author_ids = raw_book.pop('authors')
        book = Book.objects.create(**raw_book)
        # Access authors by index using the author_ids list
        author_ids = [all_authors[author_id -1].pk for author_id in author_ids]
        authors = Author.objects.filter(pk__in=author_ids)
        book.authors.set(authors)
