from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, serializers, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters import rest_framework as filters
from recipe.permissions import IsRecipeOwnerOrReadOnly, IsUserOwner
from recipe.models import Recipe, RecipeAttributeType, RecipeRate, RecipeBookMark, RecipeComment
from core.services.notifications import users as user_notifications_service


class AuthorSerializer(serializers.Serializer):
    username = serializers.CharField(read_only=True)


class RecipeAttributeTypeSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        self.relation_type = kwargs.pop('relation_type', None)
        super().__init__(*args, **kwargs)

    def create(self, validated_data):
        return RecipeAttributeType.objects.create(author=self.context['request'].user, **validated_data)
    
    def update(self, instance, validated_data):
        instance.label = validated_data.get('label', instance.label)
        instance.value = validated_data.get('value', instance.value)
        instance.save()
        return instance

    def to_internal_value(self, data):
        try:
            return RecipeAttributeType.objects.get(value=data, relation_type=self.relation_type)
        except RecipeAttributeType.DoesNotExist:
            raise serializers.ValidationError('Invalid value')

    class Meta:
        model = RecipeAttributeType
        fields = ('label', 'value', 'created_by',)
        read_only_fields = ('created_by',)


class RecipeSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    ingredients = RecipeAttributeTypeSerializer(many=True, relation_type=RecipeAttributeType.AttributeType.INGREDIENT)
    keywords = RecipeAttributeTypeSerializer(many=True, relation_type=RecipeAttributeType.AttributeType.KEYWORD)
    cuisine = RecipeAttributeTypeSerializer(relation_type=RecipeAttributeType.AttributeType.CUISINE)
    dietary = RecipeAttributeTypeSerializer(relation_type=RecipeAttributeType.AttributeType.DIETARY)

    class Meta:
        model = Recipe
        fields = (
            'id', 'title', 'description', 'instructions', 'ingredients', 'keywords',
            'cuisine', 'dietary', 'difficulty', 'time', 'author', 'rate',
            'created_at', 'updated_at',
        )
        read_only_fields = ('author', 'created_at', 'updated_at',)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        keywords = validated_data.pop('keywords')
        recipe = Recipe.objects.create(**validated_data)
        recipe.ingredients.set(ingredients)
        recipe.keywords.set(keywords)
        recipe.save()
        return recipe


class SimpleRecipeSerializer(serializers.Serializer):
    author = AuthorSerializer(read_only=True)
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    rate = serializers.IntegerField(read_only=True)


class RecipeRateSerializer(serializers.Serializer):
    rate = serializers.IntegerField(min_value=0, max_value=5, required=True)


class RecipeCommentSerializer(serializers.Serializer):
    user = serializers.CharField(source='user.username', read_only=True)
    comment = serializers.CharField(max_length=2000, required=True)
    created_at = serializers.DateTimeField(read_only=True)


class RecipeRateSerializerDetail(serializers.Serializer):
    username = serializers.CharField(source='user.username')
    rate = serializers.IntegerField(min_value=0, max_value=5)
    created_at = serializers.DateTimeField(read_only=True)


class RecipeBookMarkSerializer(serializers.Serializer):
    recipe = RecipeSerializer(read_only=True)


class RecipeFilter(filters.FilterSet):
    cuisine = filters.CharFilter(field_name='cuisine__value', lookup_expr='exact')
    dietary = filters.CharFilter(field_name='dietary__value', lookup_expr='exact')
    ingredients = filters.CharFilter(field_name='ingredients__value', lookup_expr='exact')
    keywords = filters.CharFilter(field_name='keywords__value', lookup_expr='exact')
    difficulty = filters.ChoiceFilter(field_name='difficulty', lookup_expr='exact', choices=Recipe.Difficulty.choices)
    time = filters.NumberFilter(field_name='time', lookup_expr='exact')

    class Meta:
        model = Recipe
        fields = ('cuisine', 'dietary', 'ingredients', 'keywords', 'difficulty', 'time',)


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    queryset = Recipe.objects.all()
    permission_classes = (IsRecipeOwnerOrReadOnly,)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'], url_path='save', url_name='save',
            permission_classes=[IsAuthenticated])
    def bookmark(self, request, pk=None):
        recipe = self.get_object()
        recipe.bookmark(request.user)
        user_notifications_service.likes_recipe(acting_user=request.user, recipe=recipe)
        return Response(status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='unsave', url_name='unsave',
            permission_classes=[IsAuthenticated])
    def unbookmark(self, request, pk=None):
        recipe = self.get_object()
        recipe.unbookmark(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def bookmarks(self, request):
        recipes = Recipe.objects.filter(bookmarks__user=request.user)
        serializer = SimpleRecipeSerializer(recipes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rate(self, request, pk=None):
        recipe:Recipe = self.get_object()
        serializer = RecipeRateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rate = serializer.validated_data['rate']
        recipe.add_rate(request.user, rate)
        return Response(status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def rates(self, request, pk=None):
        recipe = self.get_object()
        rates = RecipeRate.objects.filter(recipe=recipe)
        serializer = RecipeRateSerializerDetail(rates, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def comment(self, request, pk=None):
        recipe = self.get_object()
        serializer = RecipeCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.validated_data['comment']
        recipe.add_comment(request.user, comment)
        user_notifications_service.comment_recipe(acting_user=request.user, recipe=recipe, comment=comment)
        return Response(status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def comments(self, request, pk=None):
        recipe = self.get_object()
        comments = RecipeComment.objects.filter(recipe=recipe)
        serializer = RecipeCommentSerializer(comments, many=True)
        return Response(serializer.data)