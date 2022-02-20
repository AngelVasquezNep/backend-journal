from django.urls import include, path
from rest_framework import routers
from library import views

router = routers.DefaultRouter()
router.register(r'authors', views.AuthorViewSet, basename="authors")
router.register(r'books', views.BookViewSet, basename="books")

urlpatterns = router.urls