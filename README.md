# Repair Proof
**A repair proposal is not proof.** A standalone, review-first Meta AI hackathon prototype that shows the distinction.

Choose an authored failing fixture → inspect redacted evidence → review an evidence-linked repair → independently validate the patch → optionally verify before/after in an isolated container → download the review packet.

## Run locally (offline replay)
Python **3.12** is recommended. `requirements.txt` is the canonical direct
compatibility baseline; from this directory:
```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip --isolated install --index-url https://pypi.org/simple --no-cache-dir -r requirements.txt
python -m uvicorn repair_proof.app:app --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000. Installing dependencies requires package access; replay itself makes no outbound request. This is a **loopback-only single-user prototype**, not a production hosted service. Do not expose it publicly. Packets live in memory, maximum 200, and expire on restart.

`requirements.lock` is an optional conservative constraints file, not a
fresh-install portability guarantee. The current package index rejected the
required Pydantic download during a clean Python 3.12 probe; see
[CLEAN_INSTALL.md](docs/CLEAN_INSTALL.md) for exact local evidence and limits.

## Validate
```sh
python -m unittest discover -s tests -v
python -m repair_proof.evaluate
# Explicitly include the four authored holdouts only when ready:
python -m repair_proof.evaluate --include-holdouts
```
There are 12 repairable and 8 adversarial fixtures; 4 are marked holdout and excluded by default. These are synthetic, newly authored tests, **not** a benchmark of real-world/model repair quality. Offline evaluation measures policy acceptance/rejection and citation-ID validity only. Missing live/repair metrics remain `null`, never invented. Test mocks validate adapter/container contracts; the separately recorded Docker runs cover only the named authored fixtures in [VALIDATION.md](docs/VALIDATION.md), not general repair quality.

## Meta live mode — disabled by default
The browser cannot enable live mode or supply keys. After explicit authorization,
securely provide `MODEL_API_KEY` and set `RP_ENABLE_LIVE=1` in the server
environment. The direct httpx adapter calls only
`https://api.meta.ai/v1/chat/completions`, model `muse-spark-1.3`, Bearer
authentication, strict JSON Schema. It independently parses the model output
and applies policy. No OpenAI backend or fallback. Observed token usage is recorded; the bounded
runner separately reports a conservative usage-cost estimate, not an actual
billing result.

One separately authorized, two-fixture synthetic batch and its immutable-test
semantic validation are recorded in
[LIVE_SEMANTIC_VALIDATION.md](docs/LIVE_SEMANTIC_VALIDATION.md). It does not
authorize another batch or establish general repair correctness.
For a repeatable, non-inference demo record, see the sanitized
[RECORDED_LIVE_PROOF.json](docs/RECORDED_LIVE_PROOF.json); it represents prior
responses only and is not current live inference.

Official provider references supplied/verified during planning: [quickstart](https://dev.meta.ai/docs/quickstart), [models](https://dev.meta.ai/docs/models), [structured output](https://dev.meta.ai/docs/structured-output). The route returned schema-valid proposals in the documented two-call synthetic batch. This is narrow integration evidence, not a claim about every model response, account configuration or general repair quality.

## Optional isolated verification
See [SECURITY.md](docs/SECURITY.md). Off by default; there is **no host execution fallback**. Requires a trusted Docker installation/daemon and a trusted, already-local Python image. Configure `RP_ENABLE_SANDBOX=1` and `RP_SANDBOX_IMAGE=sha256:<actual 64-character local image ID>`. No image pulls, Docker installation, socket mounts, host directory mounts or credentials are performed by this application. When sandbox is disabled the UI shows an explicit preview-only explanation and disables Verify. Operator opt-in enables the attempt, not a guarantee of runtime readiness; unavailable runtime still remains preview-only.

A true verification requires the original to fail and replacement to pass the same immutable authored test in separate constrained containers. A passing replacement alone is insufficient. Policy checks are defense in depth, not a sandbox or guarantee of correctness.

## Project map
- `repair_proof/schemas.py`, `sanitize.py`: strict bounded data and redacted evidence
- `fixtures.py`: original authored source/test/replay corpus
- `meta_client.py`: opt-in Meta-only adapter
- `patch_policy.py`: independent hash/path/size/AST checks
- `verifier.py`: optional fail-closed Docker isolation
- `app.py`: API, in-memory review packets, security headers
- `web/`: dependency-free responsive UI, text-only untrusted rendering
- `tests/`: unit/API/security contract tests
- `scripts/browser_qa.py`: optional mocked-API Playwright checks (separate from the recorded-mode local QA documented in `VALIDATION.md`)
- `docs/`: design, runbook/security, provenance, demo script

## Status and scope
New source only, authored 2026-10-27; no ActionsNurse product code imported. Not deployed, published or submitted. A private credential exists outside this source tree and is not packaged. One bounded synthetic live batch was completed under separate authorization; actual container verification is recorded only for named authored fixtures, not arbitrary repairs. Hackathon eligibility/submission details must be checked against official current rules before submitting. This build is a bounded Python-fixture demonstrator, not an arbitrary-repository repair bot.

## Budgeted synthetic live evaluation
Use the separately approved CLI path, not repeated UI clicks: [LIVE_EVALUATION.md](docs/LIVE_EVALUATION.md). It caps requests at ten, sends no private source, reserves conservative exposure durably before every call, and never automatically retries. The estimated maximum ten-call exposure is $0.511600 under documented tokenizer/provider assumptions—not a provider-enforced billing cap. Existing ledgers cannot be reused. The completed two-fixture batch is documented separately; any further batch requires separate authorization.

Dependency reproducibility: earlier specialized-cloud package pins were invalid and are superseded. The direct pins in `requirements.txt` are the canonical compatibility baseline. A local project venv populated from the available direct-pin dependency closure passed all 49 tests and `pip check`; the full optional constraints lock has not been freshly reproduced from the current index. See [CLEAN_INSTALL.md](docs/CLEAN_INSTALL.md).

## Repeatable recorded Meta demo — no new API call
Choose **Recorded Meta proof** with Inclusive total or First position. These are the exact two stored, schema-validated parsed proposals from the prior authorized Meta run—not authored replay and not fresh inference. The UI shows provenance/model/hashes and separates historical Docker proof from current verification (initially NOT RUN). No key is needed. See [RECORDED_MODE.md](docs/RECORDED_MODE.md). Live runner/budget controls and direct-pin/optional-constraint installation caveats are unchanged.
