import unittest
from repair_proof.schemas import Proposal
from repair_proof.sanitize import evidence
from repair_proof.patch_policy import validate, sha

class CoreTests(unittest.TestCase):
 def proposal(self, source='def solve(x):\n    return x + 1\n', **kw):
  return Proposal.model_validate(dict(diagnosis='Fix offset', evidence_ids=['L001'], edits=[dict(path=kw.get('path','src/solution.py'), original_sha256=kw.get('hash',sha(source)), replacement=kw.get('replacement','def solve(x):\n    return x\n'))]))
 def test_redacts_secrets_and_limits(self):
  e=evidence('Authorization: Bearer supersecret\nMODEL_API_KEY=abc123\nhello')
  self.assertNotIn('supersecret',str(e)); self.assertNotIn('abc123',str(e)); self.assertEqual(e[0]['id'],'L001')
  self.assertLessEqual(len(evidence('x\n'*1000)),80)
 def test_clean_patch(self):
  self.assertTrue(validate('def solve(x):\n    return x + 1\n',self.proposal(),{'L001'})['accepted'])
 def test_paths_hash_and_code_rejected(self):
  for args in [{'path':'../a'},{'path':'/tmp/a'},{'path':'tests/test.py'},{'hash':'0'*64},{'replacement':'import os\ndef solve(x): return os.system(x)\n'},{'replacement':'def solve(x): return open(x)\n'},{'replacement':'def solve(x): return x.__class__\n'},{'replacement':'def solve(x): return eval(x)\n'}]:
   with self.subTest(args=args): self.assertFalse(validate('def solve(x):\n    return x + 1\n',self.proposal(**args),{'L001'})['accepted'])
 def test_unknown_evidence(self):
  self.assertFalse(validate('def solve(x):\n    return x + 1\n',self.proposal(),{'L002'})['accepted'])
 def test_schema_extra_rejected(self):
  with self.assertRaises(ValueError): Proposal.model_validate({'diagnosis':'x','evidence_ids':[],'edits':[],'command':'ls'})
 def test_safe_stable_dedup(self):
  self.assertTrue(validate('def solve(x):\n    return x + 1\n',self.proposal(replacement='def solve(x):\n    return list(dict.fromkeys(x))\n'),{'L001'})['accepted'])
 def test_nested_function_and_signature_change_rejected(self):
  for replacement in ['def solve(x):\n    def solve(y):\n        return y\n    return x\n','def solve(x,y):\n    return x+y\n']:
   with self.subTest(replacement=replacement): self.assertFalse(validate('def solve(x):\n    return x + 1\n',self.proposal(replacement=replacement),{'L001'})['accepted'])
