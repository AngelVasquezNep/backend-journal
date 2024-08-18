from django.urls import path, include
from rest_framework import routers
from library import views

# Using function-based views

# urlpatterns = [
#     path('books/', views.book_list),
#     path('books/<int:pk>/', views.book_detail),
# ]

# Using class-based views with APIView

# urlpatterns = [
#     path('books/', views.BookList.as_view()),
#     path('books/<int:pk>/', views.BookDetail.as_view()),
#     path('authors/', views.AuthorList.as_view()),
#     path('authors/<int:pk>/', views.AuthorDetail.as_view()),
# ]

# Using class-based views with generic views

urlpatterns = [
    path('book/', views.BookAPIView.as_view({'get': 'list', 'post': 'create'})),
    path('book/<int:pk>/', views.BookAPIView.as_view({'get': 'retrieve' })),

    # path('books/', views.BookList.as_view()),
    # path('books/<int:pk>/', views.BookDetail.as_view()),
    path('authors/', views.AuthorList.as_view()),
    path('authors/<int:pk>/', views.AuthorDetail.as_view()),
]


# Using ViewSets

# router = routers.DefaultRouter()
# router.register(r'authors', views.AuthorViewSet)
# router.register(r'books', views.BookViewSet)

# urlpatterns = [
#     path('', include(router.urls)),
# ]