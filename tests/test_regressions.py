import unittest

from fastapi.testclient import TestClient

from repair_proof.app import app
from repair_proof.packet_verifier import PacketVerificationError, verify_packet
from repair_proof.sanitize import evidence


class RegressionTests(unittest.TestCase):
    def test_authorization_token_scheme_value_is_redacted(self):
        text = ' '.join(line['text'] for line in evidence('Authorization: Token abc123def456\n'))
        self.assertNotIn('abc123def456', text)

    def test_packet_id_must_be_lowercase_hex(self):
        packet = TestClient(app).post(
            '/api/preview', json={'fixture_id': 'inclusive-total', 'mode': 'replay'}).json()
        verify_packet(packet)
        for bad in ('0x' + 'a' * 30, '+' + 'a' * 31, 'A' * 32, ' ' + 'a' * 31, '1_' + 'a' * 30):
            with self.subTest(bad=bad):
                with self.assertRaises(PacketVerificationError):
                    verify_packet({**packet, 'id': bad})


if __name__ == '__main__':
    unittest.main()
