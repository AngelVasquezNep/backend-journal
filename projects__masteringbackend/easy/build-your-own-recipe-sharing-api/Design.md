# Design

## Core

### Models

- User
- Recipe
- RecipeRating
  - User <-- RecipeRating --> Recipe
- RecipeComment
  - User <-- RecipeComment --> Recipe
- RecipeFollow
  - User <-- RecipeFollow --> User
