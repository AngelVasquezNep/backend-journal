from django.urls import path, include
from recipe.views import RecipeViewSet
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'', RecipeViewSet, basename='recipes')


urlpatterns = [
    path('', include(router.urls)),
]
