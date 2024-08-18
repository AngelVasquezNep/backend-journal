from rest_framework import serializers
from library.models import Author, Book
from core.serializers import MoneySerializer


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ('pk', 'name', 'nationality',)


class BookSerializer(serializers.ModelSerializer):
    # main_author = serializers.PrimaryKeyRelatedField(queryset=Author.objects.all())
    # main_author = serializers.IntegerField(source='main_author.id', read_only=True)
    main_author = serializers.ReadOnlyField(source='main_author.id')
    price = MoneySerializer()

    class Meta:
        model = Book
        fields = (
            'title', 'main_author', 'authors', 'year', 'language', 'cover_url',
            'sellable', 'copies', 'description', 'price',
        )


class BookSimpleSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=500)
    year = serializers.IntegerField()
    language = serializers.CharField(max_length=2)
    cover_url = serializers.CharField(max_length=500)
    sellable = serializers.BooleanField()
    copies = serializers.IntegerField()
    description = serializers.CharField()
    price = MoneySerializer()
    # authors = AuthorSerializer(many=True)

    # def create(self, validated_data):
    #     return Book.objects.create(**validated_data)

    # def update(self, instance, validated_data):
    #     instance.title = validated_data.get('title', instance.title)
    #     instance.year = validated_data.get('year', instance.year)
    #     instance.language = validated_data.get('language', instance.language)
    #     instance.cover_url = validated_data.get('cover_url', instance.cover_url)
    #     instance.sellable = validated_data.get('sellable', instance.sellable)
    #     instance.copies = validated_data.get('copies', instance.copies)
    #     instance.description = validated_data.get('description', instance.description)
    #     instance.price = validated_data.get('price', instance.price)
    #     instance.authors = validated_data.get('authors', instance.authors)
    #     instance.save()
    #     return instance

    class Meta:
        model = Book
        fields = (
            'title', 'authors', 'year', 'language', 'cover_url',
            'sellable', 'copies', 'description', 'price',
        )
