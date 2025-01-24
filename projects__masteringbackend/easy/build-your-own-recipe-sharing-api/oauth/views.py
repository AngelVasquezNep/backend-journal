from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from rest_framework.permissions import AllowAny
from .serializers import TokenObtainPairSerializer


class TokenObtainPairView(BaseTokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = TokenObtainPairSerializer
