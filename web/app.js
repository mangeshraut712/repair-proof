'use strict';
(() => {
  const $ = (id) => document.getElementById(id);
  const state = { fixtures: [], packet: null, busy: false, live: false, sandbox: false, recordedIds: [] };
  const setText = (id, value) => { $(id).textContent = value == null ? '' : String(value); };
  const readable = (value) => typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  function status(message) { setText('status', message); }
  function fail(error) { setText('error', error.message || 'The request could not be completed.'); $('error').hidden = false; }
  const selectedMode = () => document.querySelector('input[name="mode"]:checked').value;
  const unsupportedRecord = () => selectedMode() === 'recorded' && !state.recordedIds.includes($('fixture').value);
  function updateRecordedNote() {
    setText('recorded-note', unsupportedRecord() ? 'No recorded Meta proof for this fixture. Choose an available recorded case or another mode.' : 'Recorded prior Meta response — no API call.');
  }
  function busy(value) {
    state.busy = value;
    $('preview').disabled = value || !state.fixtures.length || unsupportedRecord();
    $('fixture').disabled = value || !state.fixtures.length;
    document.querySelectorAll('input[name="mode"]').forEach((input) => { input.disabled = value || (input.value === 'live' && !state.live); });
    $('verify').disabled = value || !state.sandbox || !state.packet || !state.packet.policy.accepted;
    document.querySelector('.review').setAttribute('aria-busy', String(value));
    setText('preview', value ? 'Working…' : 'Review this repair ↗');
  }
  async function request(url, body) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 90000);
    try {
      const response = await fetch(url, { method: body ? 'POST' : 'GET', headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined, signal: controller.signal });
      let result;
      try { result = await response.json(); } catch { throw new Error('The server returned an unreadable response.'); }
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Request rejected. Check the selected case and server configuration.');
      return result;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('The request timed out. No successful verification is assumed.');
      throw error;
    } finally { clearTimeout(timer); }
  }
  function badge(id, label, kind) { setText(id, label); $(id).className = `badge ${kind}`; }
  function render(packet) {
    state.packet = packet;
    $('empty').hidden = true; $('results').hidden = false;
    setText('case-title', packet.fixture.title);
    $('holdout').hidden = !packet.fixture.holdout;
    badge('source-badge', packet.mode === 'live' ? 'LIVE META RESPONSE' : packet.mode === 'recorded' ? 'RECORDED META PROOF' : 'AUTHORED REPLAY', packet.mode === 'live' ? 'pending' : 'neutral');
    setText('provenance-title', packet.mode === 'live' ? 'Live inference · independently checked' : packet.mode === 'recorded' ? 'Recorded prior Meta response — no API call' : 'Authored replay · not model-generated');
    setText('provenance', readable(packet.provenance));
    const recorded = packet.mode === 'recorded' && packet.recorded_proof;
    $('recorded-summary-panel').hidden = !recorded;
    $('recorded-details').hidden = !recorded;
    setText('recorded-summary', recorded ? `Model: ${recorded.model}
Artifact SHA-256: ${recorded.artifact_sha256}
Proposal SHA-256: ${recorded.proposal_sha256}` : '');
    setText('recorded-record', recorded ? readable(recorded) : '');
    $('evidence').replaceChildren();
    (packet.evidence || []).forEach((line) => {
      const row = document.createElement('div'); row.className = 'evidence-row';
      const id = document.createElement('span'); id.className = 'line-id'; id.textContent = line.id;
      const text = document.createElement('span'); text.className = 'line-text'; text.textContent = line.text;
      row.append(id, text); $('evidence').append(row);
    });
    setText('diagnosis', packet.proposal.diagnosis);
    $('citations').replaceChildren();
    (packet.proposal.evidence_ids || []).forEach((id) => { const chip = document.createElement('span'); chip.className = 'citation'; chip.textContent = `Evidence ${id}`; $('citations').append(chip); });
    setText('diff', packet.policy.diff || 'No displayable diff. Review the policy result below.');
    badge('policy-badge', packet.policy.accepted ? 'ACCEPTED' : 'REJECTED', packet.policy.accepted ? 'good' : 'bad');
    setText('policy-description', packet.policy.accepted ? 'The change fits the independent patch policy. Correctness still requires isolated tests.' : 'The change did not meet policy. Execution is blocked.');
    $('policy-reasons').replaceChildren();
    (packet.policy.reasons || []).forEach((reason) => { const li = document.createElement('li'); li.textContent = reason; $('policy-reasons').append(li); });
    const verification = packet.verification || { status: 'not_run', reason: 'Verification has not run.' };
    const verified = verification.status === 'verified';
    const failed = ['failed', 'rejected'].includes(verification.status);
    badge('verification-badge', String(verification.status).replaceAll('_', ' ').toUpperCase(), verified ? 'good' : failed ? 'bad' : 'pending');
    setText('verification-reason', !state.sandbox && verification.status === 'not_run' ? 'Preview only: the isolated sandbox is disabled. No tests have run in this review, and fresh verification is unavailable.' : verification.reason || 'No execution proof was provided.');
    setText('verify', verified ? 'Run verification again →' : 'Run isolated verification →');
    $('execution-details').hidden = !verification.before && !verification.after;
    setText('execution-record', readable({ before: verification.before || null, after: verification.after || null }));
    setText('metrics', readable({ metrics: packet.metrics || {}, integrity: packet.integrity || {} }));
    const id = encodeURIComponent(packet.id);
    $('download-md').href = `/api/packet/${id}?format=markdown`;
    $('download-json').href = `/api/packet/${id}?format=json`;
    busy(false);
  }
  function fixtureDetail() {
    const fixture = state.fixtures.find((item) => item.id === $('fixture').value);
    setText('fixture-detail', fixture ? `${fixture.category === 'adversarial' ? 'Adversarial case · tests the safety boundary' : 'Repairable case · tests the repair workflow'}${fixture.holdout ? ' · Excluded from default evaluation' : ''}` : '');
  }
  function resetSelection() {
    state.packet = null;
    $('results').hidden = true; $('empty').hidden = false; $('error').hidden = true;
    $('download-md').removeAttribute('href'); $('download-json').removeAttribute('href');
    badge('source-badge', 'AWAITING CASE', 'neutral');
    status('Selection changed. Review this case to load a new packet; no previous result is shown.');
  }
  $('fixture').addEventListener('change', () => { resetSelection(); fixtureDetail(); updateRecordedNote(); busy(state.busy); });
  document.querySelectorAll('input[name="mode"]').forEach((input) => input.addEventListener('change', () => {
    document.querySelectorAll('.mode-option').forEach((label) => label.classList.toggle('selected', label.querySelector('input').checked));
    resetSelection(); updateRecordedNote(); busy(state.busy);
  }));
  $('preview-form').addEventListener('submit', async (event) => {
    event.preventDefault(); if (state.busy || unsupportedRecord()) return;
    $('error').hidden = true; busy(true); status('Preparing sanitized evidence and checking the proposed patch…');
    try {
      const packet = await request('/api/preview', { fixture_id: $('fixture').value, mode: selectedMode() });
      render(packet); status('Review packet ready. Read the policy and execution results separately.');
    } catch (error) { fail(error); status('Preview did not complete. Any displayed packet is from the previous successful request.'); }
    finally { busy(false); }
  });
  $('verify').addEventListener('click', async () => {
    if (state.busy || !state.sandbox || !state.packet || !state.packet.policy.accepted) return;
    $('error').hidden = true; busy(true); status('Requesting isolated before-and-after verification…');
    try { render(await request('/api/verify', { proposal_id: state.packet.id })); status('Verification request completed. See the recorded execution status below.'); }
    catch (error) { fail(error); status('Verification request failed. No new execution result is assumed.'); }
    finally { busy(false); }
  });
  request('/api/fixtures').then((data) => {
    state.fixtures = data.fixtures; state.live = data.live_enabled === true; state.sandbox = data.sandbox_enabled === true;
    state.recordedIds = Array.isArray(data.recorded_fixture_ids) ? data.recorded_fixture_ids : [];
    setText('sandbox-note', state.sandbox ? 'Sandbox requested by the operator. Runtime readiness is checked on each run; no host fallback.' : 'Preview only: isolated sandbox is disabled. Verification is unavailable; no code will run.');
    $('fixture').replaceChildren();
    state.fixtures.forEach((fixture) => { const option = document.createElement('option'); option.value = fixture.id; option.textContent = `${fixture.title}${state.recordedIds.includes(fixture.id) ? ' · recorded Meta available' : ''}${fixture.holdout ? ' · holdout' : ''}`; $('fixture').append(option); });
    if (state.live) setText('live-note', 'Sends sanitized evidence to Meta. May incur cost.');
    fixtureDetail(); updateRecordedNote(); busy(false);
    if (!state.fixtures.length) status('No fixtures are available. Check the server configuration.');
  }).catch((error) => { fail(error); status('Cases could not be loaded. Reload after the server is available.'); });
})();
