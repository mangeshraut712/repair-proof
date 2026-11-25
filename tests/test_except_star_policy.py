import unittest

from repair_proof.patch_policy import sha, validate
from repair_proof.schemas import Proposal


class ExceptStarPolicyTests(unittest.TestCase):
    def test_except_star_try_block_is_rejected(self):
        source = 'def solve(n):\n    return n\n'
        replacement = (
            'def solve(n):\n'
            '    try:\n'
            '        return int(n)\n'
            '    except* ValueError:\n'
            '        return 0\n'
        )
        proposal = Proposal(
            diagnosis='Handle non-numeric input.',
            evidence_ids=['L001'],
            edits=[{'path': 'src/solution.py', 'original_sha256': sha(source), 'replacement': replacement}],
        )
        verdict = validate(source, proposal, {'L001'})
        self.assertFalse(verdict['accepted'], verdict)


if __name__ == '__main__':
    unittest.main()
