import tempfile, unittest
from pathlib import Path
from repair_proof.live_eval import run, BudgetError
from repair_proof.fixtures import FIXTURES
from repair_proof.schemas import Proposal
from repair_proof.patch_policy import sha

class FakeClient:
 def __init__(self,usage=None,error=False): self.calls=0;self.usage=usage;self.error=error
 def diagnose(self,lines,source):
  self.calls+=1
  if self.error: raise RuntimeError('secret-provider-error')
  f=next(f for f in FIXTURES.values() if f.source==source)
  return Proposal(diagnosis=f.diagnosis,evidence_ids=['L003'],edits=[{'path':'src/solution.py','original_sha256':sha(source),'replacement':f.replacement}]), self.usage or {'input_tokens':100,'output_tokens':200,'latency_ms':1}

class LiveEvalTests(unittest.TestCase):
 def setUp(self): self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'ledger.json';self.addCleanup(self.tmp.cleanup)
 def test_requires_explicit_approval(self):
  c=FakeClient()
  with self.assertRaises(BudgetError):run(self.path,['inclusive-total'],client=c,approved=False)
  self.assertEqual(c.calls,0)
 def test_success_reserves_before_request_and_records_usage(self):
  import json
  c=FakeClient(); original=c.diagnose
  def inspect(*a):
   d=json.loads(self.path.read_text());self.assertEqual(d['status'],'pending');self.assertEqual(d['reserved_usd'],'0.051160');return original(*a)
  c.diagnose=inspect
  d=run(self.path,['inclusive-total'],client=c,approved=True)
  self.assertEqual(d['status'],'complete');self.assertEqual(d['usage_cost_upper_usd'],'0.000975');self.assertEqual(c.calls,1)
  self.assertTrue(d['attempts'][0]['policy_accepted'])
 def test_error_halts_without_retry_even_on_restart(self):
  c=FakeClient(error=True);d=run(self.path,['inclusive-total','first-position'],client=c,approved=True)
  self.assertEqual(d['status'],'halted');self.assertEqual(c.calls,1);self.assertNotIn('secret-provider-error',self.path.read_text())
  with self.assertRaises(BudgetError):run(self.path,['inclusive-total'],client=c,approved=True)
  self.assertEqual(c.calls,1)
 def test_missing_usage_halts(self):
  c=FakeClient({'input_tokens':None,'output_tokens':10});d=run(self.path,['inclusive-total','first-position'],client=c,approved=True)
  self.assertEqual(d['status'],'halted');self.assertEqual(c.calls,1)
 def test_budget_and_call_limits_before_request(self):
  for kwargs in [{'budget_usd':'0.01'},{'budget_usd':'1.01'},{'max_calls':11},{'max_calls':0}]:
   c=FakeClient()
   with self.assertRaises(BudgetError):run(self.path,['inclusive-total'],client=c,approved=True,**kwargs)
   self.assertEqual(c.calls,0)
 def test_only_registry_and_no_duplicates(self):
  for ids in [['../../file'],['inclusive-total','inclusive-total']]:
   c=FakeClient()
   with self.assertRaises(BudgetError):run(self.path,ids,client=c,approved=True)
   self.assertEqual(c.calls,0)
 def test_completed_ledger_cannot_repeat(self):
  c=FakeClient();run(self.path,['inclusive-total'],client=c,approved=True)
  with self.assertRaises(BudgetError):run(self.path,['inclusive-total'],client=c,approved=True)
  self.assertEqual(c.calls,1)
 def test_usage_above_ceiling_halts(self):
  c=FakeClient({'input_tokens':40000,'output_tokens':10});d=run(self.path,['inclusive-total','first-position'],client=c,approved=True)
  self.assertEqual(d['status'],'halted');self.assertEqual(c.calls,1)
 def test_existing_pending_and_lock_fail_closed(self):
  self.path.write_text('{"status":"pending"}')
  with self.assertRaises(BudgetError):run(self.path,['inclusive-total'],client=FakeClient(),approved=True)
  self.path.unlink();self.path.with_suffix('.json.lock').write_text('busy')
  with self.assertRaises(BudgetError):run(self.path,['inclusive-total'],client=FakeClient(),approved=True)
 def test_uncertain_cost_is_not_reported_as_zero(self):
  c=FakeClient(error=True);d=run(self.path,['inclusive-total'],client=c,approved=True)
  self.assertIsNone(d['billed_cost_usd']);self.assertFalse(d['usage_complete']);self.assertEqual(d['usage_cost_upper_usd'],'0.000000')
 def test_maximum_batch_reservation_remains_below_one_dollar(self):
  ids=[f.id for f in FIXTURES.values() if not f.holdout and f.category=='repairable'][:10]
  c=FakeClient();d=run(self.path,ids,client=c,approved=True)
  self.assertEqual(c.calls,10);self.assertEqual(d['reserved_usd'],'0.511600')
 def test_invalid_usage_halts_no_retry(self):
  for value in [True,-1,'100']:
   with self.subTest(value=value):
    path=self.path.with_name(str(value)+'.json');c=FakeClient({'input_tokens':value,'output_tokens':10})
    d=run(path,['inclusive-total','first-position'],client=c,approved=True)
    self.assertEqual(d['status'],'halted');self.assertEqual(c.calls,1)

 def test_output_cap_violation_halts(self):
  c=FakeClient({'input_tokens':100,'output_tokens':2401});d=run(self.path,['inclusive-total','first-position'],client=c,approved=True)
  self.assertEqual(d['status'],'halted');self.assertEqual(c.calls,1)
