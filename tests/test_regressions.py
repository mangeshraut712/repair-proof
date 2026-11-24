import unittest

from repair_proof.sanitize import evidence


class RegressionTests(unittest.TestCase):
    def test_authorization_token_scheme_value_is_redacted(self):
        text = ' '.join(line['text'] for line in evidence('Authorization: Token abc123def456\n'))
        self.assertNotIn('abc123def456', text)


if __name__ == '__main__':
    unittest.main()
