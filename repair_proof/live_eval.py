"""Explicitly authorized, single-use budgeted synthetic live batch. No retries.

Budget estimates depend on documented tokenizer/overhead assumptions, not a
provider billing hard cap. Existing ledgers are NEVER resumed or overwritten.
"""
import argparse
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import tempfile
from .fixtures import FIXTURES
from .meta_client import MetaClient, MAX_REQUEST_BYTES, MAX_OUTPUT_TOKENS
from .patch_policy import validate
from .sanitize import evidence

INPUT_TOKEN_CEILING=32768
INPUT_PRICE=Decimal('1.25')
OUTPUT_PRICE=Decimal('4.25')
PER_ATTEMPT=(INPUT_PRICE*INPUT_TOKEN_CEILING+OUTPUT_PRICE*MAX_OUTPUT_TOKENS)/Decimal(1000000)

class BudgetError(Exception):
    pass

def _money(value):
    return format(value,'.6f')

def _save(path,ledger):
    # Persist pending reservation durably before any external request.
    fd,tmp=tempfile.mkstemp(prefix='.repair-proof-ledger-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            json.dump(ledger,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path)
        directory=os.open(path.parent,os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def run(path,fixture_ids,*,client=None,approved=False,budget_usd='1.00',max_calls=10):
    """One ledger, one approved batch. Pass test client only in offline tests.

    Approval must cover THIS ledger/batch. A completed, pending or halted ledger
    requires human reconciliation; deleting/renaming it is not a retry protocol.
    """
    if not approved:raise BudgetError('Explicit live-spend approval is required; no request sent')
    try: budget=Decimal(budget_usd)
    except (InvalidOperation,TypeError,ValueError):raise BudgetError('Invalid budget') from None
    if not budget.is_finite() or budget<=0 or budget>1:raise BudgetError('Budget must be positive and at most USD 1')
    if type(max_calls) is not int or not 1<=max_calls<=10:raise BudgetError('Maximum calls must be 1 through 10')
    if not fixture_ids or len(fixture_ids)>max_calls or len(set(fixture_ids))!=len(fixture_ids):raise BudgetError('Use 1 to max_calls distinct authored fixture IDs')
    if any(fid not in FIXTURES for fid in fixture_ids):raise BudgetError('Only registered synthetic fixtures are permitted')
    if PER_ATTEMPT*len(fixture_ids)>budget:raise BudgetError('Conservative reservations exceed approved budget; no request sent')
    path=Path(path).absolute()
    if path.exists() or path.is_symlink():raise BudgetError('Ledger exists; do not retry. Reconcile it with provider usage first')
    if not path.parent.is_dir():raise BudgetError('Ledger parent directory must already exist')
    if client is None:
        key=os.environ.get('MODEL_API_KEY')
        if not key:raise BudgetError('MODEL_API_KEY is missing; no request sent')
        client=MetaClient(enabled=True,key=key)
    lock=path.with_suffix(path.suffix+'.lock')
    try: fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:raise BudgetError('Batch lock exists; inspect prior process and ledger before any retry') from None
    os.close(fd)
    try:
        if path.exists() or path.is_symlink():raise BudgetError('Ledger appeared while acquiring lock; no request sent')
        ledger={'version':1,'mode':'live_synthetic_only','model':'muse-spark-1.3','status':'ready','approved_budget_usd':_money(budget),'max_calls':max_calls,'automatic_retries':0,'request_byte_cap':MAX_REQUEST_BYTES,'assumed_input_token_ceiling':INPUT_TOKEN_CEILING,'output_token_cap':MAX_OUTPUT_TOKENS,'input_usd_per_million':str(INPUT_PRICE),'output_usd_per_million':str(OUTPUT_PRICE),'reserved_usd':'0.000000','usage_cost_upper_usd':'0.000000','billed_cost_usd':None,'usage_complete':False,'attempts':[],'billing_limit_notice':'Conservative local estimate, conditional on tokenization/protocol and provider output-cap assumptions. NOT a provider billing hard cap.'}
        reserved=Decimal(0);actual=Decimal(0)
        _save(path,ledger)
        for fid in fixture_ids:
            # Reservations are never recycled, even when observed usage is lower.
            if len(ledger['attempts'])>=max_calls or reserved+PER_ATTEMPT>budget:
                ledger.update(status='halted',halt_reason='Local attempt or reservation limit');_save(path,ledger);break
            reserved+=PER_ATTEMPT
            attempt={'number':len(ledger['attempts'])+1,'fixture_id':fid,'status':'pending','reserved_usd':_money(PER_ATTEMPT)}
            ledger['attempts'].append(attempt);ledger.update(status='pending',reserved_usd=_money(reserved));_save(path,ledger)
            fixture=FIXTURES[fid];lines=evidence(fixture.log)
            try:
                proposal,metrics=client.diagnose(lines,fixture.source)
            except Exception:
                # Timeout, transport, provider or parse error may already be billed.
                attempt['status']='uncertain';ledger.update(usage_complete=False,status='halted',halt_reason='Request outcome or usage uncertain; reconcile provider usage. No retries.')
                _save(path,ledger);break
            inputs=metrics.get('input_tokens');outputs=metrics.get('output_tokens')
            if any(type(v) is not int or v<0 for v in (inputs,outputs)):
                attempt['status']='uncertain';ledger.update(usage_complete=False,status='halted',halt_reason='Missing or invalid usage; reconcile provider usage. No retries.')
                _save(path,ledger);break
            cost=(INPUT_PRICE*inputs+OUTPUT_PRICE*outputs)/Decimal(1000000)
            actual+=cost
            attempt.update(input_tokens=inputs,output_tokens=outputs,usage_cost_upper_usd=_money(cost),latency_ms=metrics.get('latency_ms'))
            ledger['usage_cost_upper_usd']=_money(actual)
            if inputs>INPUT_TOKEN_CEILING or outputs>MAX_OUTPUT_TOKENS or actual>budget:
                attempt['status']='ceiling_exceeded';ledger.update(status='halted',halt_reason='Observed usage exceeds conservative assumptions; stop and reconcile. No retries.')
                _save(path,ledger);break
            verdict=validate(fixture.source,proposal,{line['id'] for line in lines})
            attempt.update(status='measured',proposal=proposal.model_dump(),policy_accepted=verdict['accepted'],policy_reasons=verdict['reasons'],citation_ids_valid=set(proposal.evidence_ids).issubset({line['id'] for line in lines}))
            ledger['status']='ready';_save(path,ledger)
        else:
            ledger.update(status='complete',usage_complete=True);_save(path,ledger)
        return ledger
    finally:
        lock.unlink(missing_ok=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ledger',required=True,type=Path)
    p.add_argument('--fixtures',nargs='+',default=['inclusive-total'])
    p.add_argument('--max-calls',type=int,default=10)
    p.add_argument('--budget-usd',default='1.00')
    p.add_argument('--approve-live-spend',action='store_true',help='Use ONLY after explicit approval for this batch; setting the flag is not approval itself')
    args=p.parse_args()
    try: result=run(args.ledger,args.fixtures,approved=args.approve_live_spend,budget_usd=args.budget_usd,max_calls=args.max_calls)
    except BudgetError as error:p.exit(2,str(error)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='complete' else 2

if __name__=='__main__':raise SystemExit(main())
