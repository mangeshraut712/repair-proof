"""Optional mocked-API browser checks. Requires Playwright + installed Chromium.
Not part of the offline unittest suite; does not validate Meta or Docker.
"""
import json, threading
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
ROOT=str(Path(__file__).resolve().parents[1] / 'web')
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=ROOT,**kw)
 def do_GET(self):
  self.path=self.path.replace('/static/','/')
  return super().do_GET()
 def log_message(self,*a): pass
server=HTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
packet={'id':'qa-id','fixture':{'id':'one','title':'Boundary case','category':'repairable','holdout':False},'mode':'replay','provenance':'Authored replay; no live model used.','evidence':[{'id':'L001','text':'<script>window.injected=true</script> AssertionError: 2 != 3'}],'proposal':{'diagnosis':'A boundary is excluded.','evidence_ids':['L001'],'edits':[]},'policy':{'accepted':True,'reasons':[],'diff':'--- a/src/solution.py\n+++ b/src/solution.py\n-    return n\n+    return n + 1'},'verification':{'status':'not_run','reason':'No tests have been executed.'},'metrics':{'latency_ms':1,'tokens':None,'cost':None}}
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 page=browser.new_page(viewport={'width':1440,'height':1100}); errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
 def api(route):
  url=route.request.url
  if url.endswith('/api/fixtures'): result={'fixtures':[packet['fixture'],{'id':'unsupported','title':'No stored response','category':'repairable','holdout':False}],'live_enabled':False,'sandbox_enabled':False,'recorded_fixture_ids':['one']}
  elif url.endswith('/api/verify'): result={**packet,'verification':{'status':'unavailable','reason':'Isolation unavailable; execution refused.'}}
  else:
   body=json.loads(route.request.post_data or '{}')
   result=packet
   if body.get('mode')=='recorded':
    result={**packet,'mode':'recorded','provenance':'Recorded prior Meta response — no API call','recorded_proof':{'model':'muse-spark-1.3','artifact_sha256':'a'*64,'proposal_sha256':'b'*64,'previous_verification':{'status':'verified','historical':True},'untrusted_text':'<script>window.injected=true</script>'}}
  route.fulfill(status=200,content_type='application/json',body=json.dumps(result))
 page.route('**/api/**',api)
 page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_selector('#preview:not([disabled])')
 assert page.locator('input[value=live]').is_disabled()
 page.click('#preview');page.wait_for_selector('#results:not([hidden])')
 assert page.locator('#source-badge').inner_text()=='AUTHORED REPLAY'
 assert page.evaluate('window.injected') is None
 assert '<script>' in page.locator('#evidence').inner_text()
 assert page.locator('#verify').is_disabled()
 assert 'Preview only' in page.locator('#verification-reason').inner_text()
 page.check('input[value=recorded]');page.click('#preview')
 page.wait_for_function("document.getElementById('source-badge').textContent === 'RECORDED META PROOF'")
 assert 'no API call' in page.locator('#provenance-title').inner_text()
 assert page.locator('#verification-badge').inner_text()=='NOT RUN'
 assert 'muse-spark-1.3' in page.locator('#recorded-summary').inner_text()
 page.locator('#recorded-details summary').click()
 assert '<script>' in page.locator('#recorded-record').inner_text()
 assert page.evaluate('window.injected') is None
 page.select_option('#fixture','unsupported')
 assert page.locator('#preview').is_disabled()
 assert 'No recorded Meta proof' in page.locator('#recorded-note').inner_text()
 page.check('input[value=replay]'); assert page.locator('#results').is_hidden(); assert 'Selection changed' in page.locator('#status').inner_text()
 assert not page.locator('#preview').is_disabled()
 page.select_option('#fixture','one')
 # Explicit opt-in capability is distinct from runtime readiness. Reload enabled.
 def enabled_registry(route):
  route.fulfill(status=200,content_type='application/json',body=json.dumps({'fixtures':[packet['fixture'],{'id':'unsupported','title':'No stored response','category':'repairable','holdout':False}],'live_enabled':False,'sandbox_enabled':True}))
 page.route('**/api/fixtures',enabled_registry)
 page.reload();page.wait_for_selector('#preview:not([disabled])');page.click('#preview');page.wait_for_selector('#verify:not([disabled])')
 page.click('#verify');page.wait_for_function("document.getElementById('verification-badge').textContent === 'UNAVAILABLE'")
 assert 'refused' in page.locator('#verification-reason').inner_text()
 page.screenshot(path='/tmp/repair-proof-desktop.png',full_page=True)
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path='/tmp/repair-proof-mobile.png',full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
 packet['policy']={'accepted':False,'reasons':['Forbidden import.'],'diff':''}
 page.click('#preview');page.wait_for_function("document.getElementById('policy-badge').textContent === 'REJECTED'")
 assert page.locator('#verify').is_disabled()
 assert not errors, errors
 print('PASS: replay provenance, live lock, disabled sandbox capability, recorded provenance/history separation and unsupported selection, XSS-safe evidence, sandbox-unavailable state, rejection blocks verify, mobile overflow, JS console.')
 browser.close()
server.shutdown()
