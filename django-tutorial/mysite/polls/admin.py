from django.contrib import admin

from .models import (
    Question,
    Pizza,
    Topping,
    Manufacturer,
    Car,
    Person,
    Group,
    Membership,
)

admin.site.register((Question, Pizza, Topping, Manufacturer,
                    Car, Person, Group, Membership))
