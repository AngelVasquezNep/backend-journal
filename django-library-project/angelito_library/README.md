# Angelito library

## Description

Practicing Django and Django Rest Framework by creating a simple API for a library.

## Populate the database

To populate the database with some data, run the following command:

```python
python manage.py shell_plus

from library.populate_data.init import populate
populate()
```