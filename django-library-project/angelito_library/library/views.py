from django.http import Http404
from rest_framework import permissions, viewsets
from rest_framework import mixins
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from library.models import Author, Book

from library.serializers import AuthorSerializer, BookSerializer


# Using function-based views

# @api_view(['GET', 'POST'])
# def book_list(request):
#     from django.http import JsonResponse
#     from rest_framework.parsers import JSONParser
#     print(request)
#     if request.method == 'GET':
#         books = Book.objects.all()
#         serializer = BookSerializer(books, many=True)
#         return JsonResponse(serializer.data, safe=False)
#     if request.method == 'POST':
#         data = JSONParser().parse(request)
#         serializer = BookSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             return JsonResponse(serializer.data, status=201)
#         return JsonResponse(serializer.errors, status=400)


# @api_view(['GET', 'PUT', 'DELETE'])
# def book_detail(request, pk):
#     from django.http import HttpResponse, JsonResponse
#     from rest_framework.parsers import JSONParser

#     try:
#         book = Book.objects.get(pk=pk)
#     except Book.DoesNotExist:
#         return HttpResponse(status=404)

#     if request.method == 'GET':
#         serializer = BookSerializer(book)
#         return JsonResponse(serializer.data)
#     if request.method == 'PUT':
#         data = JSONParser().parse(request)
#         serializer = BookSerializer(book, data=data)
#         if serializer.is_valid():
#             serializer.save()
#             return JsonResponse(serializer.data)
#         return JsonResponse(serializer.errors, status=400)
#     if request.method == 'DELETE':
#         book.delete()
#         return HttpResponse(status=204)


# Using class-based views with APIView

# class BookList(APIView):
#     """
#     List all snippets, or create a new snippet.
#     """

#     def get(self, request, format=None):
#         books = Book.objects.all()
#         serializer = BookSerializer(books, many=True)
#         return Response(serializer.data)

#     def post(self, request, format=None):
#         serializer = BookSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=201)
#         return Response(serializer.errors, status=400)


# class BookDetail(APIView):
#     """
#     Retrieve, update or delete a snippet instance.
#     """

#     def get_object(self, pk):
#         try:
#             return Book.objects.get(pk=pk)
#         except Book.DoesNotExist:
#             raise Http404

#     def get(self, request, pk, format=None):
#         book = self.get_object(pk)
#         serializer = BookSerializer(book)
#         return Response(serializer.data)

#     def put(self, request, pk, format=None):
#         book = self.get_object(pk)
#         serializer = BookSerializer(book, data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data)
#         return Response(serializer.errors, status=400)

#     def delete(self, request, pk, format=None):
#         book = self.get_object(pk)
#         book.delete()
#         return Response(status=204)


# Using class-based views with mixins

# class BookList(
#     mixins.ListModelMixin,
#     mixins.CreateModelMixin,
#     generics.GenericAPIView,
# ):
#     queryset = Book.objects.all()
#     serializer_class = BookSerializer
#     permission_classes = (permissions.AllowAny,)

#     def get(self, request, *args, **kwargs):
#         return self.list(request, *args, **kwargs)

#     def post(self, request, *args, **kwargs):
#         return self.create(request, *args, **kwargs)


# class BookDetail(
#     mixins.RetrieveModelMixin,
#     mixins.UpdateModelMixin,
#     mixins.DestroyModelMixin,
#     generics.GenericAPIView,
# ):
#     queryset = Book.objects.all()
#     serializer_class = BookSerializer
#     permission_classes = (permissions.AllowAny,)

#     def get(self, request, *args, **kwargs):
#         return self.retrieve(request, *args, **kwargs)

#     def put(self, request, *args, **kwargs):
#         return self.update(request, *args, **kwargs)

#     def delete(self, request, *args, **kwargs):
#         return self.destroy(request, *args, **kwargs)


# Using class-based views with generics


class BookAPIView(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = (permissions.AllowAny,)


class BookList(generics.ListCreateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = (permissions.AllowAny,)


class BookDetail(generics.RetrieveAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = (permissions.AllowAny,)


class AuthorList(generics.ListAPIView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = (permissions.AllowAny,)


class AuthorDetail(generics.RetrieveAPIView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = (permissions.AllowAny,)


# Using viewsets

# class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = Author.objects.all().order_by('name')
#     serializer_class = AuthorSerializer
#     permission_classes = (permissions.AllowAny,)

# class BookViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = Book.objects.all().order_by('title')
#     serializer_class = BookSerializer
#     permission_classes = (permissions.AllowAny,)
