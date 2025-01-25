from rest_framework import permissions


class IsRecipeOwnerOrReadOnly(permissions.BasePermission):
    """
    Allow users to edit their own recipes but read-only for others.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user
