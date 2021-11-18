## En mysql

```sql
DROP DATABASE IF EXISTS simple_django_tests;
CREATE DATABASE simple_django_tests;

CREATE USER 'simple_django_tests'@'%' IDENTIFIED WITH mysql_native_password BY 'simple123';
GRANT ALL PRIVILEGES ON simple_django_tests.* TO 'simple_django_tests'@'%';
FLUSH PRIVILEGES;
```


## Comandos que corrí

1. Activar env
```
python3 -m venv venv
source venv/bin/activate
```

2. Instalar dependencias
```
pip install Django
pip install mysqlclient
```

3. Crear Django APP
```
django-admin startproject simple_app
```

4. Actualizar conexión a base de datos

En `simple_app/setting.py`
```json
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'simple_django_tests',
        'USER': 'simple_django_tests',
        'PASSWORD': 'simple123',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}
```

5. Crear Library app
```bash
python3 manage.py startapp library
```

<!-- Aquí arranca el taller -->

6. Crear Modelos

En `library/models.py`

```python
from django.db import models
from django.db.models import manager


class Books(models.Model):
    title = models.CharField(max_length=500)
    year = models.IntegerField()

    def __str__(self):
        return f'{self.title} ({self.pk})'

# Authors.objects.from_this_year()
# -> Authors.objects.filter(year=2021)

# class AuthorsManager(models.Manager):
#     def from_this_year(self):
#         self.filter(year=2021)

class Authors(models.Model):
    name = models.CharField(max_length=100)
    book = models.ForeignKey(
        'library.Books',
        on_delete=models.CASCADE,
        related_name='authors'
    )

    # manager = AuthorsManager()
```

7. Registrar APP en `simple_app/settings.py`

```python
INSTALLED_APPS = [
    'library.apps.LibraryConfig',
    ...
]
```

8. Correr migraciones

```
python3 manage.py makemigrations
python3 manage.py makemigrations library
```

Output
```
Migrations for 'library':
  library/migrations/0001_initial.py
    - Create model Books
    - Create model Authors
```

9. Ver los comandos SQL que generarón esas migraciones:
```
python3 manage.py sqlmigrate library 0001
```

Output
```sql
--
-- Create model Books
--
CREATE TABLE `library_books` (
    `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `title` varchar(500) NOT NULL,
    `year` integer NOT NULL
);
--
-- Create model Authors
--
CREATE TABLE `library_authors` (
    `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL,
    `book_id` bigint NOT NULL
);
ALTER TABLE `library_authors` ADD CONSTRAINT `library_authors_book_id_485042f9_fk_library_books_id`
    FOREIGN KEY (`book_id`) REFERENCES `library_books` (`id`);
```

10. Migrar tablas

```
python3 manage.py migrate
```

11. Entrar a la shell

```
python3 manage.py shell
```

12. Importar modelos

```python
from library.models import Books, Authors
```

13. Agregar data

```python

b = Books.objects.create(title="Cien años de soledad", year=1967)
a = Authors.objects.create(name="Gabriel García Márquez", book=b)

b = Books.objects.create(title="El señor de los anillos (Trilogía)", year=1954)
a = Authors.objects.create(name="J. R. R. Tolkien", book=b)

b = Books.objects.create(title="1984", year=1954)
a = Authors.objects.create(name="George Orwell", book=b)

b = Books.objects.create(title="Un mundo feliz", year=1954)
a = Authors.objects.create(name="Aldous Huxley", book=b)

b = Books.objects.create(title="Orgullo y prejuicio", year=1954)
a = Authors.objects.create(name="Jane Austen", book=b)

b = Books.objects.create(title="Crimen y castigo", year=1954)
a = Authors.objects.create(name="Fiódor Dostoyevski", book=b)



# the_talisman = Books.objects.create(title="The Talisman", year=1984)
# stephen_king = Authors.objects.create(name="Stephen King", book=the_talisman)
# peter_straub = Authors.objects.create(name="Peter Straub", book=the_talisman)
# it = Books.objects.create(title="It", year=1986)

# it.authors.add(stephen_king)

```
