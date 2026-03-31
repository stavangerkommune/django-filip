import unittest

from django_filip.helpers import build_url, filip_check_ok


class TestHelpers(unittest.TestCase):
    def test_filip_check_ok(self):
        self.assertEqual(filip_check_ok(), 'ok')

    def test_build_url_basic(self):
        self.assertEqual(build_url('https://api.example.com/v1', 'users'), 'https://api.example.com/v1/users')
        self.assertEqual(build_url('https://api.example.com/v1/', '/users'), 'https://api.example.com/v1/users')
        self.assertEqual(build_url('https://example.com'), 'https://example.com/')
        self.assertEqual(build_url('https://example.com/api', 'Proxy/v1'), 'https://example.com/api/Proxy/v1')

    def test_build_url_invalid_path(self):
        with self.assertRaises(ValueError):
            build_url('https://example.com', '//evil.com')
        with self.assertRaises(ValueError):
            build_url('https://example.com', 'https://evil.com')

    def test_build_url_no_base(self):
        self.assertIsNone(build_url('/'))
        self.assertIsNone(build_url(''))
