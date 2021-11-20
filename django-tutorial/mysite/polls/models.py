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
    # Choice.objects.first().question -> Me dará sólo 1 registro
    # Pero Question.objects.first().choices -> Me dará un query set
    question = models.ForeignKey(
        'polls.Question',
        related_name='choices',
        on_delete=models.CASCADE
    )
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self) -> str:
        return f'{self.choice_text} ({self.pk})'


class Person(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    def __str__(self):
        return f'({self.pk}) {self.first_name} {self.last_name}'


class Musician(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    instrument = models.CharField(max_length=100)


class Album(models.Model):
    artist = models.ForeignKey(
        'polls.Musician',
        on_delete=models.CASCADE,
        related_name="albums"
    )
    name = models.CharField(max_length=100)
    release_date = models.DateField()
    num_stars = models.IntegerField()


class Manufacturer(models.Model):
    """Manufacter company
    """
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return f'({self.pk}) {self.name}'


class Car(models.Model):
    model = models.CharField(max_length=100)
    manufacturer = models.ForeignKey(
        Manufacturer,
        related_name="cars",
        on_delete=models.CASCADE
    )

    def __str__(self) -> str:
        return f'({self.pk}) {self.model}'


Toppings = (
    ('PEPPERONI', 'PEPPERONI'),
    ('MOZZARELLA', 'MOZZARELLA'),
    ('BACON', 'BACON'),
    ('ONION', 'ONION'),
    ('CAPSICUM', 'CAPSICUM'),
    ('MUSHROOM', 'MUSHROOM'),
    ('OLIVES', 'OLIVES'),
)


Pizzas = (
    ("PEPPERONI", "PEPPERONI"),
    ("SUPREME", "SUPREME"),
    ("HAWAIIAN", "HAWAIIAN"),
    ("MARGHERITA", "MARGHERITA"),
    ("CHEESE", "CHEESE"),
)


class Topping(models.Model):
    name = models.CharField(max_length=100, choices=Toppings)

    def __str__(self) -> str:
        return f'({self.pk}) {self.name}'


class Pizza(models.Model):
    name = models.CharField(max_length=100, choices=Pizzas)
    toppings = models.ManyToManyField(
        'polls.Topping',
        related_name="pizzas"
    )

    def __str__(self) -> str:
        return f'({self.pk}) {self.name}'


class Group(models.Model):
    name = models.CharField(max_length=128)
    members = models.ManyToManyField(
        'polls.Person',
        related_name="groups",
        through='Membership',
    )

    def __str__(self):
        return f'({self.pk}) {self.name}'


class Membership(models.Model):
    person = models.ForeignKey(
        'polls.Person',
        related_name='memberships',
        on_delete=models.CASCADE,
    )
    group = models.ForeignKey(
        'polls.Group',
        related_name='memberships',
        on_delete=models.CASCADE
    )
    date_joined = models.DateField()
    invite_reason = models.CharField(max_length=64)
