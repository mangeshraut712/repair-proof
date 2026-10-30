# Validation record — 2026-10-27

## Current public-release summary
The reviewed source is public at `https://github.com/mangeshraut712/repair-proof`;
it remains undeployed and unsubmitted. Post-merge verification of code commit
`b559b05779180c304b29121b9af936aed89e2ab6` completed **62 offline tests**
plus an isolated **375×812** recorded-mode browser smoke test; see
[Current post-merge verification](#current-post-merge-verification--2026-10-30).
Historical sections below preserve their contemporaneous 35-, 49-, and
58-test results and earlier phone-QA limitations rather than describing the
current release.

## Current post-merge verification — 2026-10-30

At code commit `b559b05779180c304b29121b9af936aed89e2ab6`, an isolated
worktree ran the complete offline suite with `MODEL_API_KEY`, live mode and
sandbox mode unset:

- `python -m unittest discover -s tests -v`: **62 passed**, 0 failures/errors.
- Both authored-replay evaluations completed: 10/10 repairable accepted and
  6/6 unsafe rejected by default; 12/12 and 8/8 with visible authored holdouts.
  These remain policy metrics, not model-quality measurements.
- `pip check`, `node --check web/app.js`, tracked-file/manifest SHA-256
  verification (42 entries), and `git diff --check` passed.
- A loopback-only FastAPI server ran with live credentials and live/sandbox
  flags removed. Isolated headless Chrome at 375×812 checked both recorded
  fixtures, the explicit no-API label, historical-versus-current `NOT RUN`
  state, disabled verification, nonempty Markdown/JSON downloads, selection
  reset, long-hash wrapping, no horizontal overflow, no non-loopback page
  requests, and no page errors. This was a new local UI check; it did not make
  a model request or rerun Docker verification.

The optional Python mocked-API browser helper remains unexecuted because its
Python Playwright dependency is not bundled in the tested environment. It is
not represented as a pass; the loopback check above exercises the real app
instead.
## Actual cloud checks
- `python -m unittest discover -s tests -v`: **35 passed**, 0 failures/errors. Observed missing-module/behavior RED tests before core implementation and regression fixes, then GREEN. One preinstalled Starlette/httpx deprecation warning remains; it is not a test failure.
- `node --check web/app.js`: passed.
- Static HTML/JS checks: unique DOM IDs, every referenced ID resolved, no `innerHTML`.
- FastAPI in-process integration: registry, replay, sanitized evidence, policy, disabled sandbox, JSON/Markdown packet downloads, static root/assets, cross-origin/host refusal, streamed request body limits and concurrent verification refusal passed.
- Independent review found and resolved malformed usage handling, incorrect replay citation, chunked/malformed request-length handling, nested functions/signature changes. Regression tests included.
- `python -m repair_proof.evaluate`: 16 development cases, 10/10 repairable proposals accepted, 6/6 unsafe proposals rejected, 16/16 citation-ID references valid.
- `python -m repair_proof.evaluate --include-holdouts`: 20 authored cases, 12/12 repairable proposals accepted, 8/8 unsafe proposals rejected, 20/20 citation-ID references valid. Four holdouts explicitly included in this separate run; they are not secret/blinded.

These are **authored replay policy metrics**, not live model accuracy or semantic evidence accuracy. The post-build Docker evidence below establishes only the listed authored fixture transitions. Full machine-readable results are adjacent JSON files. A later separately authorized two-fixture live batch and its semantic before/after evidence are recorded in `LIVE_SEMANTIC_VALIDATION.md`; they do not turn these replay metrics into a general benchmark.

## Post-build Mac Docker verification
- The operator preloaded Docker Hub's official `python:3.12-slim` image for this test only, pinned locally as `sha256:12316debbfb86890f6b2d825820612741ba527ad5a44e3902759141d572bfe8f` (`linux/arm64`). The application did not pull an image.
- The final v1 API, with `RP_ENABLE_SANDBOX=1` and that pinned image, returned `verified` for the authored `inclusive-total` replay: the unchanged test exited `1` against the original and `0` against the replacement.
- The byte-identical verifier and fixture corpus also verified the authored holdout `unique-order` with the same `1` then `0` transition. This is a visible authored holdout, not a blind benchmark.
- An ordinary adversarial fixture (`attack-import`) and a holdout adversarial fixture (`attack-global`) were rejected by policy; `/api/verify` returned `409` before the verifier was called.
- A disposable inspection probe used the same fixed runner and containment settings. To inspect the completed container, it omitted only the production runner's `--rm` lifecycle flag, then removed the container successfully. Docker reported `network=none`, read-only root, user `65534:65534`, `CapDrop=[ALL]`, `no-new-privileges`, 128 MiB memory/swap, one CPU, PID limit 32, an 8 MiB `/work` tmpfs with `noexec,nosuid,nodev`, no binds or other mounts, no ports, no privilege, and no `MODEL_API_KEY` in the container environment.
- No Meta API call, provider credential, browser/screen test, deployment, publication, payment, or account creation occurred in this verification.

## Historical baseline limits
The following limits describe the original 2026-10-27 baseline; current v9
phone QA and publication status are summarized above.
- A separately authorized two-fixture Meta batch was completed after this build, with recorded usage and sandboxed semantic checks. Broader account behavior, pricing enforcement, response compatibility outside those fixtures, and general live quality remain unknown. Adapter coverage beyond those two fixtures remains MockTransport-based.
- Docker coverage is limited to the named synthetic fixtures above. It does not establish arbitrary-code safety, general repair correctness, or live-model performance. Patch source was never run on the host.
- Initial local Chromium attempt was blocked by socket permissions; escalation failed environment setup. A separate managed cloud-browser review subsequently passed desktop checks below. At that time, the phone viewport and optional mocked-API script remained unverified.
- At that time, no deployment, repository publishing, real-world repo ingestion, submission, payment or credentials had been created.

## Remaining release gates
1. The optional Python mocked-API browser helper remains unexecuted; do not represent it as a pass. The separate 2026-10-30 real-app loopback browser check is recorded above.
2. Any further Meta batch requires separate explicit approval; do not reuse the completed ledger or extrapolate from the two recorded fixtures.
3. Review official hackathon eligibility/rules/assets, then authorize submission separately.

## Runtime observed
The original cloud baseline was Python 3.12 with FastAPI 0.141.1, httpx 0.28.1, Pydantic 2.13.4, and Uvicorn 0.52.1. Those pins proved non-reproducible in this environment. The current canonical direct baseline is FastAPI 0.112.0, httpx 0.28.1, Pydantic 2.8.2, and Uvicorn 0.30.6; a separate Python 3.13.2 project venv using its available compatible closure passed the suite and `pip check`. Fresh Python 3.12 installation remains limited by current index availability; see CLEAN_INSTALL.md.

## Capability UX update
Added explicit `sandbox_enabled` capability to registry response. Disabled sandbox now disables Verify and displays a preview-only explanation before interaction. Enabled means operator opt-in, not proven runtime availability. API regression test covers both states; optional browser QA covers disabled and enabled branches. TrustedHost allowlist unchanged.

## Historical managed-browser review (after capability fix)
Reviewer exercised unchanged app source through a disposable QA copy with product TrustedHost unchanged. Actual desktop checks passed: accepted replay provenance/evidence/diff; live disabled; disabled Verify with clear preview-only explanation; adversarial socket-import rejection and blocked execution; repeated selection refresh; JSON/Markdown downloads; stopped-server failure displays Failed to fetch plus old-packet warning; restart/retry clears error and creates fresh packet. Desktop 1180×757 screenshot was inspected internally; document width 1165, no horizontal overflow. Phone viewport unverified: documented cloud browser API lacked resize/emulation. Optional mock-XSS/console script was not run; do not claim that pass.

## Historical v4 live-runner offline implementation checks
At that v4 milestone, the suite had **49 tests passed**. It added a pre-send 24,000-byte complete-request bound, 2,400 output-token cap, max-ten-attempt CLI runner, exclusive single-use ledger lock and durable pre-call reservations. Simulated tests covered explicit approval, lower/excess budget rejection, registry-only inputs, no duplicate cases, successful usage/cost recording, uncertain response halt/no retries including restart, missing/invalid usage, reported input/output cap violation, exhausted ten-call reservation, and stale lock/pending ledger refusal. Separate reviewer inspected code and assumptions. No live request or key was used during this implementation check. `usage_cost_upper_usd` is an uncached-price subtotal from observed token counts; actual billed dollars remain unknown. See LIVE_EVALUATION.md for conditional cost bounds and command.

## Post-build bounded live proof
A separately authorized two-fixture synthetic batch subsequently completed with `muse-spark-1.3`. The stored proposals for `inclusive-total` and `first-position` each revalidated against the independent policy and citation IDs, then produced the required immutable-test transition (`before=1`, `after=0`) in the network-disabled verifier. The sanitized report intentionally excludes credentials, raw model output, and private paths; see `LIVE_SEMANTIC_VALIDATION.md`. This is evidence for those two authored fixtures only, not a general repair-quality or billing claim.

## Historical v4 reproducibility correction
The original lock mistakenly pinned specialized preinstalled cloud versions (including unavailable Pydantic 2.13.4), not a portable tested environment. The direct dependency pins in `requirements.txt` now define the canonical compatibility baseline. The optional conservative constraints file remains unverified for fresh-install portability: the current trusted Python 3.12 probe stopped when the index rejected the required Pydantic 2.8.2 download. A separate project-local Python 3.13.2 venv built from the available compatible closure passed all 49 tests, `pip check`, and offline policy evaluation in that historical v4 validation. No app/UI/fixture/verifier/runner code changed at that point. Prior Docker/browser evidence is preserved. See CLEAN_INSTALL.md for exact limits.

## Recorded prior Meta mode — additive offline validation
Added a third clearly labeled mode using only the two exact parsed proposals in the preserved recorded proof artifact. Full suite now **58 tests passed** in the existing baseline-compatible Python3.12 cloud venv; this is not a new clean-install or Mac claim. Regression tests cover strict artifact/schema/hash/policy checks, missing/tampered/symlinked artifacts, unknown/unsupported fixture, no network call, current NOT RUN/unavailable independent of historical verified, and safe Markdown download fencing. JS syntax/static DOM/textContent checks passed; optional browser QA scenarios updated but not executed for this mode. Independent review found no backend blocker. No new live API calls, credentials, Docker or Mac work during this feature. Prior Mac Docker proof and installation caveats remain unchanged.

### Historical managed desktop browser — recorded mode
Independent reviewer exercised both recorded fixtures: explicit no-API provenance, actual model/hashes, historical verified JSON separate from current NOT RUN, Verify disabled without sandbox, unsupported fixture guard and clear explanation. JSON and Markdown downloads completed and contents were parsed (recorded mode, no fresh-API provenance, current not_run, historical=true). Switching modes/fixtures initially left a stale packet; fixed by hiding/resetting results, requiring fresh Review, and displaying Selection changed. Both reset paths were rechecked successfully. Desktop1180px viewport/document1165px had no horizontal overflow. No remaining observed blocker. Phone viewport and optional mocked browser script remain unverified. No live request, keys, Mac or new Docker execution used.

## Subsequent transfer/QA limits and documentation correction
The v8 Mac import did not complete: the required Library materialization helper exited1 on the normal attempt and approved external retry, with no installed archive. No Mac v8 test run is claimed. Existing earlier Mac validation remains historical evidence for its stated source version. At that v8 point, phone QA was unverified: managed cloud browser remained at1180×757 and the Mac project-local browser tooling was unavailable at that check. This documentation-only revision corrected the README’s stale blanket claim that live compatibility was unproven, narrowing it to the two documented successful synthetic calls, and clarified demo wording. Product code remained unchanged at that point.

## Local v9 offline and phone QA
This supersedes the earlier current-status claim that phone QA was unverified. The user-saved v9 archive was hash-checked before extraction. Using the existing direct-baseline-compatible Python 3.13.2 project virtual environment with live credentials and live/sandbox flags removed, the local suite completed **58 tests passed**, `pip check` reported no broken requirements, the offline evaluator exited successfully, and `node --check web/app.js` passed. No package installation, API call, ledger/key access, Docker execution, or deployment occurred.

An isolated headless Chrome run at **375×812** used the cached Playwright package and an explicit Chrome executable with no personal profile. It exercised the loopback-only application’s fixture and mode selectors, Recorded Meta proof label/provenance, historical Docker result versus current `NOT RUN` state, both nonempty packet downloads, long-hash wrapping, and selection reset. No document horizontal overflow or non-loopback page request was observed. QA found that reset hid prior packets but retained their old hidden download URLs; the reset now removes both URLs before requiring a fresh review, and the corrected behavior was retested. The optional mocked-API browser helper remains unexecuted.
