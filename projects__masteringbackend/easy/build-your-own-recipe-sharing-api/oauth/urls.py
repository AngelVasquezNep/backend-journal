from rest_framework_simplejwt.views import TokenRefreshView
from django.urls import path
from .views import TokenObtainPairView, RegisterView


urlpatterns = [
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
]
