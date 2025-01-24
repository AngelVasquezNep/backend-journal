from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from rest_framework.permissions import AllowAny
from rest_framework import generics
from django.contrib.auth import get_user_model
from .serializers import TokenObtainPairSerializer, RegisterSerializer


User = get_user_model()


class TokenObtainPairView(BaseTokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = TokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)
