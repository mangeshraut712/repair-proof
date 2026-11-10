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

 def test_redacts_github_oauth_token_prefixes(self):
  for token in ('ghp_abcdefghijklmnopqrstuvwx','gho_abcdefghijklmnopqrstuvwx','ghu_abcdefghijklmnopqrstuvwx','ghs_abcdefghijklmnopqrstuvwx','ghr_abcdefghijklmnopqrstuvwx','github_pat_abcdefghijklmnopqrstuvwx'):
   with self.subTest(token=token):
    lines=evidence('token '+token)
    self.assertNotIn(token,str(lines))
    self.assertIn('[REDACTED]',lines[0]['text'])

 def test_redacts_common_ci_token_prefixes(self):
  # Bare tokens that appear in CI logs without a "key=" label.
  for token in (
    'AKIAIOSFODNN7EXAMPLE',
    'npm_abcdefghijklmnopqrstuvwxyz0123456789abcd',
    'hf_abcdefghijklmnopqrstuvwxyz012345',
    'glpat-abcdefghijklmnopqrstuv',
    'AIzaSyA-abcdefghijklmnopqrstuvwxyz0123',
    'xoxb-SYNTHETIC_SLACK_BOT_CANARY',
    'xoxp-SYNTHETIC_SLACK_USER_CANARY',
    'gsk_abcdefghijklmnopqrstuvwxyzABCDEF0123456789',
    'xai-abcdefghijklmnopqrstuvwxyz0123456789',
    'sk_live_SYNTHETIC_STRIPE_LIVE_CANARY',
    'sk_test_SYNTHETIC_STRIPE_TEST_CANARY',
    'dop_v1_SYNTHETIC_DIGITALOCEAN_CANARY',
    'pypi-SYNTHETIC_PYPI_CANARY',
    'sntrys_SYNTHETIC_SENTRY_CANARY',
    'whsec_SYNTHETIC_STRIPE_WEBHOOK_CANARY',
    'rk_live_SYNTHETIC_STRIPE_RESTRICTED_CANARY',
    'rk_test_SYNTHETIC_STRIPE_RESTRICTED_TEST_CANARY',
    'xoxs-SYNTHETIC_SLACK_SESSION_CANARY',
    'xoxe-SYNTHETIC_SLACK_EXCHANGE_CANARY',
    'xoxc-SYNTHETIC_SLACK_CONFIG_CANARY',
    'xapp-SYNTHETIC_SLACK_APP_CANARY',
  ):
   with self.subTest(token=token):
    lines=evidence('token '+token)
    self.assertNotIn(token,str(lines))
    self.assertIn('[REDACTED]',lines[0]['text'])

 def test_redacts_slack_incoming_webhook_urls(self):
  # Assemble at runtime. A contiguous webhook URL literal trips GitHub secret scanning.
  host = 'hooks.' + 'slack.com'
  team = 'T01234567'
  channel = 'B01234567'
  token = 'abcdefghijklmnopqrstuvwx'
  bare = '/'.join((host, 'services', team, channel, token))
  for url in ('https' + '://' + bare, bare, 'http' + '://' + bare):
   with self.subTest(url=url):
    self.assertEqual(url.split('://')[-1].split('/'), [host, 'services', team, channel, token])
    lines=evidence('posted to '+url)
    self.assertEqual(lines[0]['text'], 'posted to [REDACTED]')
    self.assertNotIn(token, str(lines))
    self.assertNotIn(team, str(lines))
    self.assertNotIn(channel, str(lines))
    self.assertNotIn(url, str(lines))
    self.assertIn('[REDACTED]', lines[0]['text'])
    self.assertIn('posted to', lines[0]['text'])
 def test_redacts_quoted_and_authorization_values(self):
  # Inert markers cover ordinary JSON, shell, and HTTP log representations.
  cases = (
    ('{"api_key":"SYNTHETIC_JSON_CANARY"}', 'SYNTHETIC_JSON_CANARY'),
    ("{'client_secret': 'SYNTHETIC_SINGLE_CANARY'}", 'SYNTHETIC_SINGLE_CANARY'),
    ('password="SYNTHETIC_PREFIX secret suffix"', 'suffix'),
    ('password="SYNTHETIC_ESCAPED \\"quoted\\" tail"', 'tail'),
    ('password="SYNTHETIC_TRUNCATED suffix', 'suffix'),
    ('Bearer "SYNTHETIC_BEARER suffix"', 'suffix'),
    ('Authorization: Basic SYNTHETIC_AUTH_CANARY', 'SYNTHETIC_AUTH_CANARY'),
    ('{"Authorization": "Bearer SYNTHETIC_HEADER_CANARY"}', 'SYNTHETIC_HEADER_CANARY'),
    ('Proxy-Authorization: Basic SYNTHETIC_PROXY_CANARY', 'SYNTHETIC_PROXY_CANARY'),
  )
  for raw, marker in cases:
   with self.subTest(raw=raw):
    lines=evidence(raw)
    self.assertNotIn(marker,str(lines))
    self.assertIn('[REDACTED]',lines[0]['text'])

 def test_redaction_preserves_surrounding_evidence(self):
  lines=evidence('checkout failed; password="SYNTHETIC_WORDS with spaces"; retry checkout')
  self.assertEqual(lines,[{'id':'L001','text':'checkout failed; password=[REDACTED]; retry checkout'}])
  self.assertEqual(evidence('build passed\n3 tests passed'),[
   {'id':'L001','text':'build passed'}, {'id':'L002','text':'3 tests passed'},
  ])

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

 def test_unbounded_while_loop_is_rejected(self):
  verdict=validate('def solve(x):\n    return x + 1\n',self.proposal(replacement='def solve(x):\n    while True:\n        pass\n'),{'L001'})
  self.assertFalse(verdict['accepted'])
  self.assertIn('Disallowed Python construct: While',verdict['reasons'])

 def test_direct_recursion_remains_rejected(self):
  verdict=validate('def solve(x):\n    return x + 1\n',self.proposal(replacement='def solve(x):\n    return solve(x)\n'),{'L001'})
  self.assertFalse(verdict['accepted'])
  self.assertIn('Call is not allowlisted',verdict['reasons'])
