import copy, hashlib, json, unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from repair_proof.app import app
from repair_proof import recorded

class RecordedTests(unittest.TestCase):
 def setUp(self): self.raw=recorded.ARTIFACT.read_bytes();self.data=json.loads(self.raw);self.client=TestClient(app)
 def test_recorded_no_network_and_never_fresh_proof(self):
  with patch('httpx.Client.send',side_effect=AssertionError('No network allowed')):
   # ASGI test transport is not httpx.Client.send; use direct endpoint for network assertion.
   from repair_proof.app import preview
   from repair_proof.schemas import Preview
   p=preview(Preview(fixture_id='inclusive-total',mode='recorded'))
  self.assertEqual(p['mode'],'recorded');self.assertEqual(p['verification']['status'],'not_run')
  self.assertIn('no API call',p['provenance']);self.assertTrue(p['recorded_proof']['previous_verification']['historical'])
  self.assertIsNone(p['metrics']['input_tokens']);self.assertEqual(p['recorded_proof']['model'],'muse-spark-1.3')
  self.assertTrue(p['policy']['accepted']);self.assertEqual(p['proposal'],self.data['fixtures'][0]['recorded_parsed_proposal']['proposal'])
 def test_both_available_and_unknown_unsupported(self):
  d=self.client.get('/api/fixtures').json();self.assertEqual(d['recorded_fixture_ids'],['inclusive-total','first-position'])
  for fid in d['recorded_fixture_ids']:self.assertEqual(self.client.post('/api/preview',json={'fixture_id':fid,'mode':'recorded'}).status_code,200)
  self.assertEqual(self.client.post('/api/preview',json={'fixture_id':'clamp-ceiling','mode':'recorded'}).status_code,409)
 def test_missing_and_tampered_artifact_fail_closed(self):
  for raw in [b'{}',self.raw.replace(b'Off-by-one',b'Tampered!!')]:
   with patch.object(recorded.Path,'read_bytes',return_value=raw):
    with self.assertRaises(recorded.RecordedError):recorded.load_records()
  with patch.object(recorded.Path,'read_bytes',side_effect=FileNotFoundError):
   self.assertEqual(self.client.post('/api/preview',json={'fixture_id':'inclusive-total','mode':'recorded'}).status_code,503)
 def test_independent_validation_even_if_artifact_digest_updated(self):
  mutations=[lambda d:d['fixtures'][0].update(fixture_id='../../etc/passwd'),lambda d:d['fixtures'][0]['input_hashes_sha256'].update(source='0'*64),lambda d:d['fixtures'][0]['recorded_parsed_proposal']['proposal'].update(command='whoami'),lambda d:d['fixtures'][0]['docker_semantic_validation']['semantic_input_hashes_sha256'].update(test_contract='0'*64)]
  for mutate in mutations:
   d=copy.deepcopy(self.data);mutate(d);raw=json.dumps(d).encode()
   with patch.object(recorded.Path,'read_bytes',return_value=raw),patch.object(recorded,'ARTIFACT_SHA256',hashlib.sha256(raw).hexdigest()):
    with self.assertRaises(recorded.RecordedError):recorded.load_records()
 def test_download_provenance_and_history_not_current(self):
  p=self.client.post('/api/preview',json={'fixture_id':'inclusive-total','mode':'recorded'}).json()
  for fmt in ['json','markdown']:
   r=self.client.get('/api/packet/'+p['id']+'?format='+fmt);self.assertEqual(r.status_code,200);self.assertIn('no API call',r.text);self.assertIn('not_run',r.text);self.assertIn('historical',r.text)
 def test_policy_rejects_changed_edit_even_with_recomputed_checksums(self):
  d=copy.deepcopy(self.data);r=d['fixtures'][0];p=r['recorded_parsed_proposal']['proposal'];p['edits'][0]['path']='tests/test_contract.py'
  r['recorded_parsed_proposal']['canonical_sha256']=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  raw=json.dumps(d).encode()
  with patch.object(recorded.Path,'read_bytes',return_value=raw),patch.object(recorded,'ARTIFACT_SHA256',hashlib.sha256(raw).hexdigest()):
   with self.assertRaises(recorded.RecordedError):recorded.load_records()
 def test_current_disabled_verification_never_inherits_historical_success(self):
  import os
  p=self.client.post('/api/preview',json={'fixture_id':'first-position','mode':'recorded'}).json()
  with patch.dict(os.environ,{'RP_ENABLE_SANDBOX':'0'}):r=self.client.post('/api/verify',json={'proposal_id':p['id']}).json()
  self.assertEqual(r['verification']['status'],'unavailable');self.assertEqual(r['recorded_proof']['previous_verification']['status'],'verified');self.assertTrue(r['recorded_proof']['previous_verification']['historical'])
 def test_recorded_diagnosis_untrusted_text_stays_in_safe_download(self):
  records=recorded.load_records();p=records['inclusive-total']['proposal'];p.diagnosis='```\n<script>alert(1)</script>\n```'
  with patch('repair_proof.app.load_records',return_value=records):r=self.client.post('/api/preview',json={'fixture_id':'inclusive-total','mode':'recorded'}).json()
  download=self.client.get('/api/packet/'+r['id']+'?format=markdown')
  self.assertTrue(download.headers['content-type'].startswith('text/markdown'));self.assertIn('attachment;',download.headers['content-disposition']);self.assertIn('````json',download.text)
  self.assertIn("script-src 'self'",download.headers['content-security-policy'])
 def test_symlink_artifact_rejected(self):
  with patch.object(recorded.Path,'is_symlink',return_value=True):
   with self.assertRaises(recorded.RecordedError):recorded.load_records()
