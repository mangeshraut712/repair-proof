import json, unittest
import httpx
from repair_proof.meta_client import MetaClient, ProviderError
from repair_proof.patch_policy import sha
from repair_proof.schemas import Proposal
from repair_proof.verifier import verify
from repair_proof.fixtures import FIXTURES

class AdapterTests(unittest.TestCase):
 def test_live_gate_no_request(self):
  with self.assertRaises(ProviderError): MetaClient(enabled=False,key='secret').diagnose([], 'x')
 def test_malformed_provider_is_safe(self):
  def reply(request): return httpx.Response(200,json={'choices':[]})
  with self.assertRaises(ProviderError): MetaClient(enabled=True,key='secret',transport=httpx.MockTransport(reply)).diagnose([], 'x')
 def test_contract_and_usage(self):
  def reply(request):
   self.assertEqual(str(request.url),'https://api.meta.ai/v1/chat/completions')
   body=json.loads(request.content); self.assertEqual(body['model'],'muse-spark-1.3'); self.assertTrue(body['response_format']['json_schema']['strict'])
   self.assertEqual(request.headers['authorization'],'Bearer secret')
   return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'diagnosis':'fix','evidence_ids':['L001'],'edits':[{'path':'src/solution.py','original_sha256':'0'*64,'replacement':'def solve(x): return x'}]})}}],'usage':{'prompt_tokens':100,'completion_tokens':30}})
  p,m=MetaClient(enabled=True,key='secret',transport=httpx.MockTransport(reply)).diagnose([{'id':'L001','text':'failure'}], 'x')
  self.assertEqual(p.diagnosis,'fix'); self.assertEqual(m['input_tokens'],100)
 def test_verifier_disabled(self):
  f=next(iter(FIXTURES.values()))
  proposal=Proposal(diagnosis=f.diagnosis,evidence_ids=['L003'],edits=[{'path':'src/solution.py','original_sha256':sha(f.source),'replacement':f.replacement}])
  self.assertEqual(verify(f,proposal,enabled=False)['status'],'unavailable')
 def test_null_usage_does_not_crash(self):
  def reply(request): return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'diagnosis':'fix','evidence_ids':['L003'],'edits':[{'path':'src/solution.py','original_sha256':'0'*64,'replacement':'def solve(x): return x'}]})}}],'usage':None})
  p,m=MetaClient(enabled=True,key='secret',transport=httpx.MockTransport(reply)).diagnose([], 'x')
  self.assertIsNone(m['input_tokens'])
 def test_bad_provider_shapes_and_secret_errors(self):
  for data in [[],None,{'choices':[None]},{'choices':[{'message':None}]},{'choices':[{'message':{'content':'secret-invalid'}}]}]:
   with self.subTest(data=data):
    def reply(request): return httpx.Response(200,json=data)
    with self.assertRaises(ProviderError) as caught: MetaClient(enabled=True,key='secret',transport=httpx.MockTransport(reply)).diagnose([], 'x')
    self.assertNotIn('secret',str(caught.exception))
 def test_every_schema_object_is_closed_and_required(self):
  from repair_proof.schemas import Proposal
  def walk(x):
   if isinstance(x,dict):
    if x.get('type')=='object':
     self.assertFalse(x['additionalProperties']); self.assertEqual(set(x['required']),set(x['properties']))
    for v in x.values(): walk(v)
   elif isinstance(x,list):
    for v in x: walk(v)
  walk(Proposal.model_json_schema())
 def test_oversized_prompt_refused_before_transport(self):
  def reply(request): self.fail('Oversized prompt was sent')
  with self.assertRaises(ProviderError): MetaClient(enabled=True,key='secret',transport=httpx.MockTransport(reply)).diagnose([], 'x'*25000)
