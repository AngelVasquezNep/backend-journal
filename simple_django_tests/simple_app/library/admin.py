from django.contrib import admin

from library.models import Author, Book

admin.site.register((Author, Book))
