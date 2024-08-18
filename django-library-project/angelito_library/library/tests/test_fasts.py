from django.test import TestCase


class CustomConfig:
    def __getattribute__(self, name: str) -> str:
        return name.upper() + '_VALUE'


class FastTestCase(TestCase):
    def test_custom_config(self):
        config = CustomConfig()
        self.assertEqual(config.DEBUG, 'DEBUG_VALUE')
        self.assertEqual(config.SECRET_KEY, 'SECRET_KEY_VALUE')

