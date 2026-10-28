"""Loopback-only development app; no repository paths or executable commands accepted."""
import json
import os
import threading
import time
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .fixtures import FIXTURES
from .meta_client import MetaClient, ProviderError
from .patch_policy import sha, validate
from .sanitize import evidence
from .schemas import Preview, Proposal, Verify
from .verifier import verify
from .recorded import load_records, RecordedError

ROOT=Path(__file__).resolve().parent.parent
app=FastAPI(title='Repair Proof',docs_url=None,redoc_url=None)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['localhost','127.0.0.1','testserver'])
app.mount('/static',StaticFiles(directory=ROOT/'web'),name='static')
PACKETS={}
LOCK=threading.Lock()
VERIFY_SLOT=threading.BoundedSemaphore(1)

def live_enabled():
    return os.environ.get('RP_ENABLE_LIVE')=='1' and bool(os.environ.get('MODEL_API_KEY'))

@app.middleware('http')
async def security(request: Request, call_next):
    if request.method=='POST':
        origin=request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            return Response('Cross-origin requests refused',status_code=403)
        try:
            size=int(request.headers.get('content-length','0'))
            if size<0: raise ValueError()
        except ValueError:
            return Response('Invalid content length',status_code=400)
        if size>4096: return Response('Request too large',status_code=413)
        body=bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body)>4096: return Response('Request too large',status_code=413)
        request._body=bytes(body)
    response=await call_next(request)
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    return response

@app.get('/')
def index(): return FileResponse(ROOT/'web'/'index.html')

@app.get('/api/fixtures')
def fixtures():
    try: recorded_ids=list(load_records())
    except RecordedError: recorded_ids=[]
    return {'fixtures':[{'id':f.id,'title':f.title,'category':f.category,'holdout':f.holdout} for f in FIXTURES.values()], 'live_enabled':live_enabled(), 'sandbox_enabled':os.environ.get('RP_ENABLE_SANDBOX')=='1', 'recorded_fixture_ids':recorded_ids}

@app.post('/api/preview')
def preview(req: Preview):
    f=FIXTURES.get(req.fixture_id)
    if not f: raise HTTPException(404,'Unknown fixture')
    lines=evidence(f.log)
    started=time.monotonic()
    recorded_proof=None
    if req.mode=='replay':
        proposal=Proposal(diagnosis=f.diagnosis,evidence_ids=[lines[2]['id']],edits=[{'path':'src/solution.py','original_sha256':sha(f.source),'replacement':f.replacement}])
        metrics={'latency_ms':round((time.monotonic()-started)*1000),'input_tokens':None,'output_tokens':None,'cost_usd':None}
        provenance='Replay — newly authored expected proposal, NOT a Meta model response. Logs are synthetic fixture evidence.'
    elif req.mode=='recorded':
        try: records=load_records()
        except RecordedError as error: raise HTTPException(503,str(error)) from None
        if f.id not in records: raise HTTPException(409,'No recorded Meta proof for this fixture. Choose inclusive-total or first-position; no API call made.')
        proposal=records[f.id]['proposal'];recorded_proof=records[f.id]['proof']
        metrics={'latency_ms':None,'input_tokens':None,'output_tokens':None,'cost_usd':None}
        provenance='Recorded prior Meta response — no API call. Model: muse-spark-1.3. Stored parsed proposal, not a raw HTTP response. Historical Docker results are not current verification.'
    else:
        try: proposal,metrics=MetaClient(enabled=live_enabled(),key=os.environ.get('MODEL_API_KEY')).diagnose(lines,f.source)
        except ProviderError as e: raise HTTPException(503,str(e)) from None
        provenance='Live Meta API — muse-spark-1.3. Independent policy is not verification. Logs are synthetic fixture evidence.'
    packet={'id':uuid.uuid4().hex,'fixture':{'id':f.id,'title':f.title,'category':f.category,'holdout':f.holdout},'mode':req.mode,'provenance':provenance,'evidence':lines,'proposal':proposal.model_dump(),'policy':validate(f.source,proposal,{l['id'] for l in lines}),'verification':{'status':'not_run','reason':'No code has been executed. Policy acceptance is not repair proof.'},'metrics':metrics,'integrity':{'source_sha256':sha(f.source),'test_sha256':sha(f.test_source),'replacement_sha256':sha(proposal.edits[0].replacement)}}
    if recorded_proof is not None: packet['recorded_proof']=recorded_proof
    with LOCK:
        if len(PACKETS)>=200: PACKETS.pop(next(iter(PACKETS)))
        PACKETS[packet['id']]=packet
    return packet

def get_packet(pid):
    with LOCK: p=PACKETS.get(pid)
    if not p: raise HTTPException(404,'Unknown or expired proposal; previews are in-memory and limited to 200')
    return p

@app.post('/api/verify')
def verification(req: Verify):
    p=get_packet(req.proposal_id)
    if not p['policy']['accepted']: raise HTTPException(409,'Policy rejected: execution prohibited')
    f=FIXTURES[p['fixture']['id']]
    # Revalidate stored proposal; client cannot supply replacement paths or commands.
    proposal=Proposal.model_validate(p['proposal'])
    if not validate(f.source,proposal,{l['id'] for l in p['evidence']})['accepted']: raise HTTPException(409,'Stored proposal failed revalidation')
    if not VERIFY_SLOT.acquire(blocking=False): raise HTTPException(429,'Another isolated verification is running; retry when it completes')
    try:
        result=verify(f,proposal,enabled=os.environ.get('RP_ENABLE_SANDBOX')=='1')
    finally:
        VERIFY_SLOT.release()
    with LOCK: p['verification']=result
    return p

@app.get('/api/packet/{pid}')
def packet(pid: str, format: str='json'):
    p=get_packet(pid)
    if format not in {'json','markdown'}: raise HTTPException(400,'Supported formats: json, markdown')
    if format=='json': content=json.dumps(p,indent=2); media='application/json'; suffix='json'
    else:
        # All untrusted text remains inside a dynamically sized code fence.
        raw=json.dumps(p,indent=2,ensure_ascii=True)
        fence='`'*(max([len(x) for x in __import__('re').findall(r'`+',raw)]+[2])+1)
        content=f"# Repair Proof review packet\n\n{p['provenance']}\n\nPolicy: {'accepted' if p['policy']['accepted'] else 'rejected'}. Verification: {p['verification']['status']}.\n\n{fence}json\n{raw}\n{fence}\n"; media='text/markdown'; suffix='md'
    return Response(content,media_type=media,headers={'Content-Disposition':f'attachment; filename="repair-proof-{p["id"]}.{suffix}"'})
