from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, serializers, mixins, status
from rest_framework.validators import UniqueValidator
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from core.models import UserFollowing

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

    @action(detail=False, methods=['GET'])
    def followers(self, request):
        followers = request.user.followers.all()
        serializer = UserFollowersSerializer(followers, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['GET'])
    def following(self, request):
        following = request.user.following.all()
        serializer = UserFollowingSerializer(following, many=True)
        return Response(serializer.data)


class UserFollowersSerializer(serializers.Serializer):
    username = serializers.CharField(source='user.username', read_only=True)


class UserFollowingSerializer(serializers.ModelSerializer):
    following = serializers.CharField(source='following.username', read_only=True)

    class Meta:
        model = UserFollowing
        fields = ('following', 'created_at',)


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = User.objects.none()
    serializer_class = UserFollowingSerializer
    pagination_class = None

    @action(detail=True, methods=['post'])
    def follow(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        UserFollowing.objects.get_or_create(user=request.user, following=user)
        return Response(status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'])
    def unfollow(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        UserFollowing.objects.filter(user=request.user, following=user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
