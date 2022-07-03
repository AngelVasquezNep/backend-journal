from django.db import models
from django.db.models.query import QuerySet
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    ``created_at`` and ``updated_at`` fields.
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
        db_index=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        blank=True,
        null=True,
        db_index=True
    )

    class Meta:
        abstract = True

class SoftDeletionQuerySet(QuerySet):
    pass

class SoftDeletionManager(models.Manager):
    queryset_class = SoftDeletionQuerySet

    def __init__(self, *args, **kwargs):
        self.alive_only = kwargs.pop('alive_only', True)
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        query_set_class = self.queryset_class

        if self.alive_only:
            return query_set_class(self.model, using=self._db).filter(deleted_at=None)
        return query_set_class(self.model, using=self._db)


class SoftDeletionModel(models.Model):
    deleted_at = models.DateTimeField(blank=True, null=True, db_index=True)
    objects = SoftDeletionManager()
    all_objects = SoftDeletionManager(alive_only=False)

    def delete(self, *args, **kwargs):
        self._meta.model.objects.filter(
            pk=self.pk).update(deleted_at=timezone.now())


class BaseModel(SoftDeletionModel, TimeStampedModel):
    class Meta:
        abstract = True
