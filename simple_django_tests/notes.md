DATABASE: simple_django_tests

CREATE USER 'simple_django_tests'@'%' IDENTIFIED WITH mysql_native_password BY 'simple123';
GRANT ALL PRIVILEGES ON simple_django_tests.* TO 'simple_django_tests'@'%';
FLUSH PRIVILEGES;
