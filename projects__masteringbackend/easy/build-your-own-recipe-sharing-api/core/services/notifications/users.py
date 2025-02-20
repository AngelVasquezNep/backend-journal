from __future__ import annotations
from typing import TYPE_CHECKING
from django.contrib.auth import get_user_model
from core.services.notifications.notifications import EmailService


if TYPE_CHECKING:
    from core import models
    from recipe import models


User = get_user_model()


def likes_recipe(*, acting_user: models.User, recipe: models.Recipe):
    body = f'{acting_user.username} likes your recipe {recipe.title}'
    EmailService.send_one(recipe.author.email, 'New Like', body)


def comment_recipe(*, acting_user: models.User, recipe: models.Recipe, comment: str):
    body = f'{acting_user.username} comments your recipe {recipe.title} with: "{comment}"'
    EmailService.send_one(recipe.author.email, 'New Comment', body)


def new_follower(*, acting_user: models.User, target_user: models.User):
    body = f'{acting_user.username} starts following you'
    EmailService.send_one(target_user.email, 'New Follower', body)
