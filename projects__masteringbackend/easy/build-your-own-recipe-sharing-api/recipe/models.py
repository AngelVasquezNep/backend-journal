from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class Recipe(models.Model):
    class Difficulty(models.TextChoices):
        SUPER_EASY = 'SUPER_EASY'
        EASY = 'EASY'
        MEDIUM = 'MEDIUM'
        HARD = 'HARD'
        SUPER_HARD = 'SUPER_HARD'

    title = models.CharField(max_length=100)
    description = models.TextField(max_length=200)
    instructions = models.TextField(max_length=2000)

    ingredients = models.ManyToManyField('recipe.RecipeAttributeType', related_name='recipe_ingredients')
    keywords = models.ManyToManyField('recipe.RecipeAttributeType', related_name='recipe_keywords')
    cuisine = models.ForeignKey('recipe.RecipeAttributeType', related_name='recipe_cuisine', on_delete=models.CASCADE)
    dietary = models.ForeignKey('recipe.RecipeAttributeType', related_name='recipe_dietary', on_delete=models.CASCADE)

    difficulty = models.CharField(
        max_length=100,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM)
    time = models.IntegerField(default=0)

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('-id',)
        unique_together = ('title', 'author',)


class CreatedBy(models.TextChoices):
    SYSTEM = 'SYSTEM'
    COMMUNITY = 'COMMUNITY'


class RecipeAttributeType(models.Model):
    class AttributeType(models.TextChoices):
        INGREDIENT = 'INGREDIENT'
        KEYWORD = 'KEYWORD'
        CUISINE = 'CUISINE'
        DIETARY = 'DIETARY'

    label = models.CharField(max_length=100)
    value = models.CharField(max_length=100)
    created_by = models.CharField(max_length=30, choices=CreatedBy.choices, default=CreatedBy.SYSTEM)
    relation_type = models.CharField(max_length=30, choices=AttributeType.choices)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipe_created_attributes')

    def __str__(self):
        return f"{self.relation_type} - {self.value} ({self.created_by})"

    class Meta:
        unique_together = ('value', 'relation_type',)
        ordering = ('-id',)
