import unittest
from fastapi.testclient import TestClient
from repair_proof.app import app

class AppTests(unittest.TestCase):
 def setUp(self): self.client=TestClient(app)
 def test_registry_and_replay_packet(self):
  fixtures=self.client.get('/api/fixtures').json()['fixtures']; self.assertEqual(len(fixtures),20)
  r=self.client.post('/api/preview',json={'fixture_id':fixtures[0]['id'],'mode':'replay'})
  self.assertEqual(r.status_code,200); p=r.json(); self.assertEqual(p['mode'],'replay'); self.assertEqual(p['verification']['status'],'not_run')
  self.assertTrue(p['policy']['accepted'])
  self.assertEqual(self.client.get('/api/packet/'+p['id']).status_code,200)
  self.assertIn('Replay',self.client.get('/api/packet/'+p['id']+'?format=markdown').text)
  v=self.client.post('/api/verify',json={'proposal_id':p['id']}).json(); self.assertEqual(v['verification']['status'],'unavailable')
 def test_invalid_inputs(self):
  self.assertEqual(self.client.post('/api/preview',json={'fixture_id':'../../etc/passwd','mode':'replay'}).status_code,404)
  self.assertEqual(self.client.post('/api/verify',json={'proposal_id':'a'*32,'command':'whoami'}).status_code,422)
  self.assertEqual(self.client.get('/api/packet/'+'a'*32).status_code,404)
 def test_live_disabled(self):
  fid=self.client.get('/api/fixtures').json()['fixtures'][0]['id']
  self.assertEqual(self.client.post('/api/preview',json={'fixture_id':fid,'mode':'live'}).status_code,503)
 def test_adversarial_rejected(self):
  fs=self.client.get('/api/fixtures').json()['fixtures']
  for f in fs:
   if f['category']=='adversarial':
    p=self.client.post('/api/preview',json={'fixture_id':f['id'],'mode':'replay'}).json()
    self.assertFalse(p['policy']['accepted'],f['id'])
    self.assertEqual(self.client.post('/api/verify',json={'proposal_id':p['id']}).status_code,409)
 def test_evidence_citation_points_to_failure(self):
  fid=self.client.get('/api/fixtures').json()['fixtures'][0]['id']
  p=self.client.post('/api/preview',json={'fixture_id':fid,'mode':'replay'}).json()
  cited=[l['text'] for l in p['evidence'] if l['id'] in p['proposal']['evidence_ids']]
  self.assertTrue(any('AssertionError' in x for x in cited))
 def test_bad_length_header(self):
  r=self.client.post('/api/preview',headers={'content-length':'nonsense'},content='{}')
  self.assertEqual(r.status_code,400)
 def test_chunked_body_limit(self):
  r=self.client.post('/api/preview',content=iter([b'x'*4097]),headers={'content-type':'application/json'})
  self.assertEqual(r.status_code,413)
 def test_static_security_and_origin(self):
  r=self.client.get('/'); self.assertEqual(r.status_code,200); self.assertIn("default-src 'self'",r.headers['content-security-policy'])
  self.assertEqual(self.client.get('/static/app.js').status_code,200)
  self.assertEqual(self.client.post('/api/preview',json={},headers={'origin':'https://evil.example'}).status_code,403)
  self.assertEqual(self.client.get('/',headers={'host':'evil.example'}).status_code,400)
 def test_verification_concurrency_is_bounded(self):
  from repair_proof.app import VERIFY_SLOT
  fid=self.client.get('/api/fixtures').json()['fixtures'][0]['id']
  p=self.client.post('/api/preview',json={'fixture_id':fid,'mode':'replay'}).json()
  VERIFY_SLOT.acquire()
  try: self.assertEqual(self.client.post('/api/verify',json={'proposal_id':p['id']}).status_code,429)
  finally: VERIFY_SLOT.release()
 def test_sandbox_capability_is_explicit_and_disabled_by_default(self):
  from unittest.mock import patch
  import os
  with patch.dict(os.environ,{'RP_ENABLE_SANDBOX':'0'}):
   self.assertIs(self.client.get('/api/fixtures').json()['sandbox_enabled'],False)
  with patch.dict(os.environ,{'RP_ENABLE_SANDBOX':'1'}):
   self.assertIs(self.client.get('/api/fixtures').json()['sandbox_enabled'],True)
