from rest_framework import viewsets, serializers
from django_filters import rest_framework as filters
from recipe.permissions import IsRecipeOwnerOrReadOnly
from recipe.models import Recipe, RecipeAttributeType

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
            'cuisine', 'dietary', 'difficulty', 'time', 'author',
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


class RecipeFilter(filters.FilterSet):
    cuisine = filters.CharFilter(field_name='cuisine__value', lookup_expr='exact')
    dietary = filters.CharFilter(field_name='dietary__value', lookup_expr='exact')
    ingredients = filters.CharFilter(field_name='ingredients__value', lookup_expr='exact')
    keywords = filters.CharFilter(field_name='keywords__value', lookup_expr='exact')
    difficulty = filters.CharFilter(field_name='difficulty', lookup_expr='exact')
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
