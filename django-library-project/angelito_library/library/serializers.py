from rest_framework import serializers
from library.models import Author, Book


class AuthorSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Author
        fields = ('name', 'nationality',)


class BookSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Book
        fields = (
            'title', 'authors', 'year', 'language', 'cover_url',
            'sellable', 'copies', 'description',
        )
