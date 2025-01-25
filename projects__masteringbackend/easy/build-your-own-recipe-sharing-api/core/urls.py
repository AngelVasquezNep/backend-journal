from django.urls import path, include
from .views import ProfileViewSet
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
# router.register(r'profile', ProfileViewSet, basename='profile')


urlpatterns = [
    path('profile/', ProfileViewSet.as_view({'get': 'retrieve', 'put': 'update'})),
    path('', include(router.urls)),
]
