from django.test import TestCase
from djmoney.money import Money
from library.models import Author, Book
from library.serializers import BookSimpleSerializer


AUTHOR = {
    "name": "Gabriel García Márquez",
    "nationality": "COL"
},

BOOK = {
    "title": "Cien años de soledad",
    "authors": [1],
    "year": 1967,
    "language": "es",
    "cover_url": "https://placehold.co/600x400",
    "price": {
        "amount": "20.00",
        "currency": "USD"
    },
    "sellable": True,
    "copies": 5,
    "description": "A magical realism novel by Gabriel García Márquez."
}


class BooksSerializerTestCase(TestCase):
    def setUp(self):
        author = Author.objects.create(
            name='Gabriel Garcia Marquez',
        )
        _BOOK = BOOK.copy()
        authors = _BOOK.pop('authors')
        price = _BOOK.pop('price')
        book = Book.objects.create(
            **_BOOK,
            price=Money(**price)
        )
        book.authors.add(author)

    def test_book_serializer(self):
        book = Book.objects.first()
        serializer = BookSimpleSerializer(book)
        data: dict = serializer.data
        self.assertEqual(data['title'], 'Cien años de soledad')
        self.assertEqual(data['price']['amount'], 20)
        self.assertEqual(data['price']['currency'], 'USD')
        # self.assertEqual(len(data['authors']), 1)
        # self.assertEqual(data['authors'][0]['name'], 'Gabriel Garcia Marquez')

    def test_book_serializer_create(self):
        serializer = BookSimpleSerializer(data=BOOK)
        serializer.is_valid(raise_exception=True)
        book: Book = serializer.save()
        self.assertEqual(book.title, 'Cien años de soledad')
        self.assertEqual(book.price.amount, 20)
        self.assertEqual(str(book.price.currency), 'USD')
        # self.assertEqual(book.authors.count(), 0)
