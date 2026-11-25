import unittest

from repair_proof.packet_verifier import PacketVerificationError, verify_packet


class PacketUnhashableValueTests(unittest.TestCase):
    def test_unhashable_mode_is_rejected_not_crash(self):
        with self.assertRaises(PacketVerificationError):
            verify_packet({'mode': []})

    def test_unhashable_fixture_id_is_rejected_not_crash(self):
        packet = {
            'id': '0' * 32,
            'fixture': {'id': []},
            'mode': 'replay',
            'provenance': '',
            'evidence': [],
            'proposal': {},
            'policy': {},
            'verification': {},
            'metrics': {},
            'integrity': {},
        }
        with self.assertRaises(PacketVerificationError):
            verify_packet(packet)


if __name__ == '__main__':
    unittest.main()
