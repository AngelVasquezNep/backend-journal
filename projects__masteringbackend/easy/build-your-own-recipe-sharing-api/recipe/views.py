from rest_framework import viewsets, serializers
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


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    queryset = Recipe.objects.all()
    permission_classes = (IsRecipeOwnerOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
