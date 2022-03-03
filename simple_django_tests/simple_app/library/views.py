from rest_framework import serializers, viewsets, permissions
from rest_framework.response import Response
from library.models import Author, Book


class BookAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ('id', 'name',)


class BookSerializer(serializers.ModelSerializer):
    authors = BookAuthorSerializer(many=True)

    class Meta:
        model = Book
        fields = ('id', 'title', 'year', 'authors')


class AuthorBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ('id', 'title', 'year',)


class AuthorSerializer(serializers.ModelSerializer):
    books = AuthorBookSerializer(many=True, read_only=True)

    class Meta:
        model = Author
        fields = ('id', 'name', 'books',)



class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        book = self.get_object()
        authors = request.data.pop('authors')
        serializer = self.get_serializer(book, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        book.authors.set(authors)

        return Response(serializer.data)
