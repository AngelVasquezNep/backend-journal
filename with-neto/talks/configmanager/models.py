from django.db import models

# Create your models here.
# Manager -> Maneja la comunicación con la base
# Queryset -> Constructor de queries

# python manage.py shell_plus --print-sql


class Config(models.Model):
    name = models.CharField(max_length=250)


class App(models.Model):
    version = models.IntegerField(null=False)
    active_config = models.ForeignKey(
        'Config',
        on_delete=models.SET_NULL,
        null=True,
    )


for a in App.objects.all():
    print(a.version, a.active_version)


# Cuando tenemos la referencia a otra tabla
# usamos select_reñetad
# App.objects.all().select_releated('active_config')
