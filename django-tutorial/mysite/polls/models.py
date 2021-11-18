import datetime

from django.db import models
from django.utils import timezone


class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')

    def __str__(self) -> str:
        return f'{self.question_text} ({self.pk})'

    def was_published_recently(self) -> bool:
        """Note: It works over a Question instance.

        q = Question.objects.first()
        q.was_published_recently()
        """
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)


class Choice(models.Model):
    question = models.ForeignKey(
        'polls.Question',
        related_name='choices',
        on_delete=models.CASCADE
    )
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self) -> str:
        return f'{self.choice_text} ({self.pk})'
