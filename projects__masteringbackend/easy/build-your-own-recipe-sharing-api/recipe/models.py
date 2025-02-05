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

    rate = models.IntegerField(default=0) # 0-5 -> Average rate of the recipe from RecipeRate model

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('-id',)
        unique_together = ('title', 'author',)

    def bookmark(self, user):
        RecipeBookMark.objects.get_or_create(recipe=self, user=user)

    def unbookmark(self, user):
        RecipeBookMark.objects.filter(recipe=self, user=user).delete()

    def add_rate(self, user, rate):
        RecipeRate.objects.update_or_create(recipe=self, user=user, defaults={'rate': rate})
        self.rate = self.rates.aggregate(models.Avg('rate'))['rate__avg'] or 0
        self.save()

    def add_comment(self, user, comment):
        RecipeComment.objects.create(recipe=self, user=user, comment=comment)



class RecipeAttributeType(models.Model):
    class CreatedBy(models.TextChoices):
        SYSTEM = 'SYSTEM'
        COMMUNITY = 'COMMUNITY'

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


class RecipeRate(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='rates')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rates')
    rate = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('recipe', 'user',)
        ordering = ('-id',)

    def __str__(self):
        return f"{self.recipe.title} | {self.user.username} rates {self.rate} stars"


class RecipeBookMark(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='bookmarks')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('recipe', 'user',)
        ordering = ('-id',)
    
    def __str__(self):
        return f"{self.recipe.title} - {self.user.username}"


class RecipeComment(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-id',)

    def __str__(self):
        return f"{self.recipe.title} - {self.user.username} - {self.comment[:20]}"