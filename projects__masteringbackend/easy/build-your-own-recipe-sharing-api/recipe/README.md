# Recipes

## Create recipes

```python
recipe = Recipe.objects.create(
    title='Spaghetti Carbonara',
    description='A classic Italian pasta dish.',
    instructions='1. Cook the pasta according to the package instructions. 2. In a large skillet, cook the pancetta until crispy. 3. In a bowl, whisk together the eggs, cheese, and black pepper. 4. Drain the pasta and add it to the skillet with the pancetta. 5. Remove from heat and add the egg mixture. 6. Toss until the pasta is coated. 7. Serve with additional cheese and black pepper.',
    cuisine=RecipeAttributeType.objects.get(label='Italian'),
    dietary=RecipeAttributeType.objects.get(label='Vegetarian'),
    difficulty=Recipe.Difficulty.EASY,
    time=30,
    author=User.objects.get_system_user(),
)
recipe.ingredients.add(
    RecipeAttributeType.objects.get(label='Pasta'),
    RecipeAttributeType.objects.get(label='Egg'),
    RecipeAttributeType.objects.get(label='Pancetta'),
    RecipeAttributeType.objects.get(label='Parmesan Cheese'),
    RecipeAttributeType.objects.get(label='Black Pepper'),
)
recipe.keywords.add(
    RecipeAttributeType.objects.get(label='Quick'),
    RecipeAttributeType.objects.get(label='Comfort Food'),
    RecipeAttributeType.objects.get(label='Family-Friendly'),
)
recipe.save()
```

## Recipes (json) examples

```json
[
  {
    "title": "Sopa de mamá",
    "description": "Sopa de pollo",
    "instructions": "1. Calentar agua. 2. Agregar piezas de pollo. 3. Agregar verduras y sal 4. Dejar cocinar por 30 min",
    "ingredients": ["CHICKEN", "SALT", "CARROT", "POTATOES"],
    "keywords": ["EASY"],
    "cuisine": "MEXICAN",
    "dietary": "DIABETIC_FRIENDLY",
    "difficulty": "EASY",
    "time": 30
  },
  {
    "title": "Pizza napolitana",
    "description": "Pizza with tomato sauce, mozzarella, and basil.",
    "instructions": "1. Preheat the oven to 500°F. 2. Roll out the pizza dough. 3. Spread the tomato sauce over the dough. 4. Add the mozzarella and basil. 5. Bake for 10-12 minutes or until the crust is golden brown.",
    "ingredients": ["TOMATO", "MOZZARELLA", "BASIL", "OLIVE_OIL"],
    "keywords": ["VEGAN"],
    "cuisine": "ITALIAN",
    "dietary": "VEGETARIAN",
    "difficulty": "MEDIUM",
    "time": 30
  }
]
```
