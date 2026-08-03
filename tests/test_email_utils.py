import os
import unittest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app.utils import email_utils


class EmailUtilsTests(unittest.TestCase):
    def setUp(self):
        os.environ['TESTING_MODE'] = 'true'
        os.environ['TESTING_EMAIL'] = 'qa@example.com'

    def tearDown(self):
        os.environ.pop('TESTING_MODE', None)
        os.environ.pop('TESTING_EMAIL', None)

    def test_build_message_routes_to_test_recipient_when_testing_mode_is_enabled(self):
        msg = email_utils._build_message('Subject', ['client@example.com'], 'Body content')

        self.assertEqual(msg['To'], 'qa@example.com')
        self.assertEqual(msg['X-Original-To'], 'client@example.com')

    def test_never_send_real_mail_env_switch_routes_mail_to_safe_address(self):
        os.environ['NEVER_SEND_REAL_MAIL'] = 'true'
        os.environ.pop('TESTING_MODE', None)
        os.environ['TESTING_EMAIL'] = 'safe@example.com'

        msg = email_utils._build_message('Subject', ['client@example.com'], 'Body content')

        self.assertEqual(msg['To'], 'safe@example.com')
        self.assertEqual(msg['X-Original-To'], 'client@example.com')


if __name__ == '__main__':
    unittest.main()
