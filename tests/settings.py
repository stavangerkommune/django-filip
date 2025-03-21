# tests/settings.py
SECRET_KEY = "fake-key-for-testing"
INSTALLED_APPS = [
    "django_filip.core",
    "django_filip.hent",
    "django_filip.open",
    "django_filip.pool",
    "django_filip.send",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
