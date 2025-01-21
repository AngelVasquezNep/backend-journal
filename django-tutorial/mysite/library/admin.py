from django.contrib import admin

from library.models import Book, BookInstance, Author, Genre, Lang

admin.site.register(Book)
admin.site.register(BookInstance)
admin.site.register(Author)
admin.site.register(Genre)
admin.site.register(Lang)

