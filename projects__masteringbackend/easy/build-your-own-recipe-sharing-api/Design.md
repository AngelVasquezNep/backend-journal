# Design

## Core

### Models

- User
- Recipe
  - User --> Recipe
- BookMark
  - User <-- BookMark --> Recipe
- RecipeRating
  - User <-- RecipeRating --> Recipe
- RecipeComment
  - User <-- RecipeComment --> Recipe
- UserFollow
  - User <-- UserFollow --> User
