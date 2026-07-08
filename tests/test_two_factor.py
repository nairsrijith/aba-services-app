import unittest

from app.utils.two_factor import generate_totp_secret, generate_totp_code, verify_totp_code, build_otpauth_uri


class TwoFactorTests(unittest.TestCase):
    def test_generate_totp_secret_returns_b32_string(self):
        secret = generate_totp_secret()
        self.assertTrue(secret)
        self.assertRegex(secret, r'^[A-Z2-7]+=*$')

    def test_generate_and_verify_totp_code(self):
        secret = 'JBSWY3DPEHPK3PXP'
        code = generate_totp_code(secret, for_time=1700000000)
        self.assertTrue(verify_totp_code(secret, code, for_time=1700000000))
        self.assertFalse(verify_totp_code(secret, '000000', for_time=1700000000))

    def test_build_otpauth_uri_includes_required_parts(self):
        uri = build_otpauth_uri('user@example.com', 'JBSWY3DPEHPK3PXP', 'ABA Services')
        self.assertIn('otpauth://totp/', uri)
        self.assertIn('user%40example.com', uri)
        self.assertIn('ABA%20Services', uri)


if __name__ == '__main__':
    unittest.main()
