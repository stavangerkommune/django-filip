# Django-Filip
![status: active](https://img.shields.io/badge/status-active-blue) [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) ![license: BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-green)

## Background
django-filip is a light-weight integration layer for use with Django. It allows you to easily connect to different kinds of servers, using API, MSSQL and SFTP.

django-filip is currently in early development, and breaking changes may happen at any time. Make sure to pin your exact version!


## Quickstart
Installing with uv
```console
uv add django-filip
```

Add to installed apps
```python
# settings.py

INSTALLED_APPS = [
    ...
    'django-filip',
    ...
```

Make sure to do database migrations:
```console
uv run manage.py migrate
```

## Usage examples
Set up connections in Django-Admin

### API Request
```python
from django_filip.models import Connection

connection = Connection.objects.get(id=1)
response = connection.client.get('v1/objects/suppliers?param=1')
items = response.json()
```

### Database Query
```python
from django_filip.models import Connection

connection = Connection.objects.get(id=1)
query = 'SELECT * FROM suppliers'
results = connection.client.execute_query(query)
```

### SFTP Upload
```python
from django_filip.models import Connection

connection = Connection.objects.get(id=1)
with document.file.open('rb') as file:
    response = connection.client.upload(file, '/remote/path', 'document.pdf')
```

For more examples, see [examples.md](docs/examples.md)

## Compatibility
This app is designed and tested to work with the Django LTS versions:
- Django 5.2.x

Other versions (ex. 5.0.x, 5.1.x) are not officially supported. Make sure to lock in on an LTS-version in 'pyproject.toml':

For Django 5.2.x:
```toml
dependencies = ["django>=5.2,<5.3"]
```