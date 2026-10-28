import json
import os
import subprocess
import unittest
from unittest.mock import patch

from repair_proof.fixtures import FIXTURES
from repair_proof.patch_policy import sha
from repair_proof.schemas import Proposal
from repair_proof.verifier import verify

IMAGE = 'sha256:' + 'a' * 64


def completed(code=0, output=''):
    return subprocess.CompletedProcess([], code, output, '')


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.fixture = FIXTURES['inclusive-total']

    def proposal(self, replacement=None):
        return Proposal(
            diagnosis=self.fixture.diagnosis,
            evidence_ids=['L003'],
            edits=[{
                'path': 'src/solution.py',
                'original_sha256': sha(self.fixture.source),
                'replacement': self.fixture.replacement if replacement is None else replacement,
            }],
        )

    @patch('repair_proof.verifier.subprocess.run')
    def test_disabled_never_invokes_docker(self, run):
        self.assertEqual(verify(self.fixture, self.proposal())['status'], 'unavailable')
        run.assert_not_called()

    @patch.dict(os.environ, {'RP_SANDBOX_IMAGE': IMAGE})
    @patch('repair_proof.verifier.shutil.which', return_value='/usr/bin/docker')
    @patch('repair_proof.verifier.subprocess.run')
    def test_policy_rejected_loop_proposal_never_reaches_docker(self, run, which):
        proposal = Proposal(
            diagnosis='Attempt an unbounded loop',
            evidence_ids=['L003'],
            edits=[{
                'path': 'src/solution.py',
                'original_sha256': sha(self.fixture.source),
                'replacement': 'def solve(n):\n    while True:\n        pass\n',
            }],
        )
        try:
            result = verify(self.fixture, proposal, enabled=True)
        except AttributeError as error:
            self.fail(f'verify must reject an invalid structured proposal before Docker: {error}')
        self.assertEqual(result['status'], 'unverified')
        self.assertIn('policy', result['reason'].lower())
        run.assert_not_called()

    @patch.dict(os.environ, {'RP_SANDBOX_IMAGE': IMAGE})
    @patch('repair_proof.verifier.shutil.which', return_value='/usr/bin/docker')
    @patch('repair_proof.verifier.subprocess.run')
    def test_unstructured_replacement_never_reaches_docker(self, run, which):
        result = verify(self.fixture, self.fixture.replacement, enabled=True)
        self.assertEqual(result['status'], 'unverified')
        run.assert_not_called()

    @patch.dict(os.environ, {'RP_SANDBOX_IMAGE': 'python:latest'})
    @patch('repair_proof.verifier.subprocess.run')
    def test_mutable_image_reference_rejected(self, run):
        self.assertEqual(verify(self.fixture, self.proposal(), True)['status'], 'unavailable')
        run.assert_not_called()

    @patch.dict(os.environ, {'RP_SANDBOX_IMAGE': IMAGE})
    @patch('repair_proof.verifier.shutil.which', return_value='/usr/bin/docker')
    @patch('repair_proof.verifier.subprocess.run')
    def test_verified_requires_failed_before_passed_after_and_hardening(self, run, which):
        run.side_effect = [completed(output=IMAGE+'\n'), completed(output=json.dumps({'exit_code': 1, 'output': 'FAILED'})), completed(output=json.dumps({'exit_code': 0, 'output': 'OK'}))]
        result = verify(self.fixture, self.proposal(), True)
        self.assertEqual(result['status'], 'verified')
        calls = run.call_args_list[1:]
        self.assertEqual(len(calls), 2)
        for call in calls:
            command = call.args[0]
            for flag in ['--network', '--read-only', '--user', '--cap-drop', '--security-opt', '--cpus', '--memory', '--pids-limit', '--tmpfs', '--pull=never']:
                self.assertIn(flag, command)
            self.assertNotIn('--volume', command)
            self.assertNotIn('-v', command)
            self.assertEqual(json.loads(call.kwargs['input'])['tests'], self.fixture.test_source)
            self.assertNotIn('MODEL_API_KEY', call.kwargs['env'])
        self.assertNotEqual(calls[0].args[0][calls[0].args[0].index('--name')+1], calls[1].args[0][calls[1].args[0].index('--name')+1])

    @patch.dict(os.environ, {'RP_SANDBOX_IMAGE': IMAGE})
    @patch('repair_proof.verifier.shutil.which', return_value='/usr/bin/docker')
    @patch('repair_proof.verifier.subprocess.run')
    def test_already_passing_before_is_not_verified(self, run, which):
        run.side_effect = [completed(output=IMAGE), completed(output=json.dumps({'exit_code': 0, 'output': 'OK'})), completed(output=json.dumps({'exit_code': 0, 'output': 'OK'}))]
        self.assertEqual(verify(self.fixture, self.proposal(), True)['status'], 'unverified')

    @patch.dict(os.environ, {'RP_SANDBOX_IMAGE': IMAGE})
    @patch('repair_proof.verifier.shutil.which', return_value='/usr/bin/docker')
    @patch('repair_proof.verifier.subprocess.run')
    def test_timeout_removes_container_and_fails_closed(self, run, which):
        run.side_effect = [completed(output=IMAGE), subprocess.TimeoutExpired('docker', 20), completed()]
        result = verify(self.fixture, self.proposal(), True)
        self.assertEqual(result['status'], 'unverified')
        self.assertEqual(run.call_args_list[-1].args[0][1:3], ['rm', '-f'])

    @patch.dict(os.environ, {'RP_SANDBOX_IMAGE': IMAGE})
    @patch('repair_proof.verifier.shutil.which', return_value='/usr/bin/docker')
    @patch('repair_proof.verifier.subprocess.run')
    def test_nonzero_docker_exit_is_infrastructure_failure(self, run, which):
        run.side_effect = [completed(output=IMAGE), completed(code=125, output='failed')]
        self.assertEqual(verify(self.fixture, self.proposal(), True)['status'], 'unverified')

    @patch.dict(os.environ, {'RP_SANDBOX_IMAGE': IMAGE})
    @patch('repair_proof.verifier.shutil.which', return_value='/usr/bin/docker')
    @patch('repair_proof.verifier.subprocess.run')
    def test_image_must_already_exist(self, run, which):
        run.return_value = completed(code=1)
        self.assertEqual(verify(self.fixture, self.proposal(), True)['status'], 'unavailable')
        self.assertEqual(run.call_count, 1)


if __name__ == '__main__':
    unittest.main()
