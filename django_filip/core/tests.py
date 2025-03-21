from django.test import TestCase

from django_filip.core.apps import CoreConfig


class CoreAppTests(TestCase):
    def test_app_config(self):
        self.assertEqual(CoreConfig.name, "django_filip.core")
