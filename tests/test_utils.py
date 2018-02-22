from unittest import TestCase
import settings

from tests.utils import updated_setting


class TestContext(TestCase):
    @classmethod
    def tearDownClass(cls):
        del settings.TEST

    def test_with_context_when_successful(self):
        settings.TEST = 'first'
        with updated_setting('TEST', 'second'):
            self.assertEqual('second', settings.TEST)
        self.assertEqual('first', settings.TEST)

    def test_with_context_when_error(self):
        settings.TEST = 'first'
        try:
            with updated_setting('TEST', 'second'):
                self.assertEqual('second', settings.TEST)
                raise ValueError('Test error')
        except ValueError:
            self.assertEqual('first', settings.TEST)