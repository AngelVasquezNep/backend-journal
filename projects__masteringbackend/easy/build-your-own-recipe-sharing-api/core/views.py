from django.contrib.auth import get_user_model
from rest_framework import viewsets, serializers, mixins
from rest_framework.validators import UniqueValidator
from rest_framework.permissions import IsAuthenticated

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(
        required=False,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email',)


class ProfileViewSet(
        viewsets.GenericViewSet,
        mixins.UpdateModelMixin,
        mixins.RetrieveModelMixin):
    permission_classes = (IsAuthenticated,)
    queryset = User.objects.none()
    serializer_class = ProfileSerializer
    pagination_class = None

    def get_object(self):
        return self.request.user
