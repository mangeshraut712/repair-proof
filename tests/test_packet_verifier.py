import json
import copy
import multiprocessing
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from repair_proof.app import app
from repair_proof import packet_verifier
from repair_proof.packet_verifier import PacketVerificationError


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PACKET = ROOT / 'scripts' / 'verify_packet.py'


def _fifo_swap_worker(path, result_pipe):
    """Swap the checked regular file for a FIFO immediately after lstat."""
    original = Path(path)
    real_lstat = os.lstat
    swapped = False

    def swap_after_check(candidate, *args, **kwargs):
        nonlocal swapped
        metadata = real_lstat(candidate, *args, **kwargs)
        if not swapped and os.fspath(candidate) == os.fspath(original):
            original.unlink()
            os.mkfifo(original)
            swapped = True
        return metadata

    try:
        with patch.object(packet_verifier.os, 'lstat', side_effect=swap_after_check):
            packet_verifier.verify_packet_file(original)
    except PacketVerificationError as error:
        result_pipe.send(('rejected', str(error)))
    except BaseException as error:  # Keep the parent diagnosis deterministic.
        result_pipe.send(('unexpected', repr(error)))
    else:
        result_pipe.send(('accepted', None))
    finally:
        result_pipe.close()


class PacketVerifierTests(unittest.TestCase):
    def setUp(self):
        self._offline_env = patch.dict(os.environ, {'RP_ENABLE_SANDBOX': '0'}, clear=False)
        self._offline_env.start()
        self.addCleanup(self._offline_env.stop)
        self.client = TestClient(app)

    def review_packet(self, mode):
        response = self.client.post(
            '/api/preview',
            json={'fixture_id': 'inclusive-total', 'mode': mode},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def run_verifier(self, packet):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'packet.json'
            path.write_text(json.dumps(packet), encoding='utf-8')
            return self.run_verifier_path(path)

    def run_verifier_path(self, path):
        return subprocess.run(
            [sys.executable, str(VERIFY_PACKET), str(path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_accepts_a_current_recorded_packet_from_the_app(self):
        """A verifier regression catches removal of recorded-packet validation."""
        result = self.run_verifier(self.review_packet('recorded'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('consistent with this source release', result.stdout)

    def test_accepts_the_second_current_recorded_packet_from_the_app(self):
        """A verifier regression catches a fixture-specific recorded-proof assumption."""
        response = self.client.post(
            '/api/preview',
            json={'fixture_id': 'first-position', 'mode': 'recorded'},
        )
        self.assertEqual(response.status_code, 200)
        result = self.run_verifier(response.json())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('consistent with this source release', result.stdout)

    def test_accepts_an_authored_replay_packet_from_the_app(self):
        """A verifier regression catches an implementation that only accepts recordings."""
        result = self.run_verifier(self.review_packet('replay'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('consistent with this source release', result.stdout)

    def test_rejects_a_recorded_packet_with_a_tampered_replacement(self):
        """A verifier regression catches removal of replacement/hash checks."""
        packet = copy.deepcopy(self.review_packet('recorded'))
        packet['proposal']['edits'][0]['replacement'] = 'def solve(n):\n    return 0\n'
        result = self.run_verifier(packet)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('INVALID:', result.stderr)

    def test_rejects_a_changed_policy_verdict(self):
        """A verifier regression catches trust in a packet-supplied policy result."""
        packet = copy.deepcopy(self.review_packet('replay'))
        packet['policy']['accepted'] = False
        result = self.run_verifier(packet)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('INVALID:', result.stderr)

    def test_rejects_a_recorded_packet_with_changed_history(self):
        """A verifier regression catches a forged historical-proof marker."""
        packet = copy.deepcopy(self.review_packet('recorded'))
        packet['recorded_proof']['previous_verification']['historical'] = False
        result = self.run_verifier(packet)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('INVALID:', result.stderr)

    def test_rejects_a_packet_that_promotes_history_to_current_execution(self):
        """A verifier regression catches historical Docker proof posed as current work."""
        packet = copy.deepcopy(self.review_packet('recorded'))
        packet['verification'] = {'status': 'verified', 'reason': 'Historical result copied forward'}
        result = self.run_verifier(packet)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('INVALID:', result.stderr)

    def test_rejects_an_actual_packet_after_a_verification_attempt(self):
        """A checker PASS must never be read as validation of an execution result."""
        packet = self.review_packet('replay')
        response = self.client.post('/api/verify', json={'proposal_id': packet['id']})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['verification']['status'], 'unavailable')
        result = self.run_verifier(response.json())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('INVALID:', result.stderr)

    def test_rejects_an_unregistered_fixture(self):
        """A verifier regression catches a packet that escapes the fixed fixture corpus."""
        packet = copy.deepcopy(self.review_packet('replay'))
        packet['fixture']['id'] = 'not-a-registered-fixture'
        result = self.run_verifier(packet)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('INVALID:', result.stderr)

    def test_rejects_a_symlink_packet_even_when_its_content_is_valid(self):
        """A verifier regression catches a path check that follows a supplied symlink."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'packet.json'
            target.write_text(json.dumps(self.review_packet('recorded')), encoding='utf-8')
            link = Path(directory) / 'packet-link.json'
            link.symlink_to(target)
            result = self.run_verifier_path(link)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('INVALID:', result.stderr)

    def test_rejects_an_oversized_packet_even_when_its_json_is_valid(self):
        """A verifier regression catches unbounded reads of a downloaded packet."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'packet.json'
            path.write_text(json.dumps(self.review_packet('replay')) + (' ' * 70000), encoding='utf-8')
            result = self.run_verifier_path(path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('INVALID:', result.stderr)

    def test_rejects_a_path_replaced_by_a_symlink_after_lstat(self):
        """A verifier regression catches a check-then-open symlink race."""
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / 'packet.json'
            replacement = Path(directory) / 'replacement.json'
            payload = json.dumps(self.review_packet('recorded'))
            original.write_text(payload, encoding='utf-8')
            replacement.write_text(payload, encoding='utf-8')
            real_lstat = os.lstat
            replaced = False

            def swap_after_check(path, *args, **kwargs):
                nonlocal replaced
                metadata = real_lstat(path, *args, **kwargs)
                if not replaced and os.fspath(path) == os.fspath(original):
                    original.unlink()
                    original.symlink_to(replacement)
                    replaced = True
                return metadata

            with patch.object(packet_verifier.os, 'lstat', side_effect=swap_after_check):
                with self.assertRaises(PacketVerificationError):
                    packet_verifier.verify_packet_file(original)

    @unittest.skipUnless(
        os.name == 'posix' and hasattr(os, 'mkfifo') and 'fork' in multiprocessing.get_all_start_methods(),
        'requires POSIX FIFOs and fork',
    )
    def test_rejects_a_fifo_swapped_in_after_lstat_without_blocking(self):
        """A regular-file check must not let a path race block on a FIFO open."""
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / 'packet.json'
            original.write_text('{}', encoding='utf-8')
            context = multiprocessing.get_context('fork')
            receiver, sender = context.Pipe(duplex=False)
            process = context.Process(target=_fifo_swap_worker, args=(str(original), sender))
            process.start()
            sender.close()
            process.join(1)
            if process.is_alive():
                process.terminate()
                process.join()
                self.fail('FIFO swap blocked while opening the packet path')
            self.assertEqual(process.exitcode, 0)
            self.assertTrue(receiver.poll())
            status, detail = receiver.recv()
            self.assertEqual(status, 'rejected')
            self.assertEqual(detail, 'Packet file must be a regular file')

    def test_fails_closed_when_nonblocking_open_is_unavailable(self):
        """A platform without the anti-FIFO flag must not silently risk a block."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'packet.json'
            path.write_text('{}', encoding='utf-8')
            with patch.object(packet_verifier.os, 'O_NONBLOCK', None):
                with self.assertRaises(PacketVerificationError) as caught:
                    packet_verifier.verify_packet_file(path)
        self.assertEqual(str(caught.exception), 'Safe packet file opening is unavailable')
