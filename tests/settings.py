# tests/settings.py
SECRET_KEY = "fake-key-for-testing"
INSTALLED_APPS = [
    "django_filip",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
