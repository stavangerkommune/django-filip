# Django-Filip
![status: aktiv](https://img.shields.io/badge/status-aktiv-blue) [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) ![licence: MIT](https://img.shields.io/badge/license-MIT-blue)

## Bakgrunn
Filip begynte som et system for å teleportere filer mellom regnskapsprogram og nisjesystem.

Programmet gir i dag mulighet for å behandle data og synkronisere data mellom systemer.


## Quickstart
Installer med pip
```console
pip install django-filip
```

Legg til i installerte apper
```python
# setup.py

INSTALLED_APPS = [
    ...
    # Følgende app er påkrevd:
    'django-filip.core', # Grunnfunksjonalitet

    # Resten kan velges
    'django-filip.hent', # For å hente fra filer og systemer
    'django-filip.send', # For å sende bearbeidede data
    'django-filip.pool', # Dokumentbibliotek
    'django-filip.open', # Åpne data
```

Oppdater urls.py
```python
# urls.py

urlpatterns = [
    ...
    path('django_filip/', include('django_filip.core.urls')),
    ...
]
```

Etter du har lagt disse til kjører du en migrering
```console
python manage.py migrate
```


## Utvikling (uv)
```console
git clone https://github.com/stavangerkommune/django-filip
cd django-filip
uv sync
```
