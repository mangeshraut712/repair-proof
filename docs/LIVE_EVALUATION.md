# Authorized synthetic live evaluation — bounded runner
Implementation has been tested offline only. No key is handled or live request made during implementation. A later operator must have explicit user approval for the specific batch; the CLI flag records that intent, it does not create approval.

## One-command smoke run (ONLY after approval and secure key setup)
Use a fresh, existing private working directory, a dedicated Meta key securely provided as `MODEL_API_KEY`, and do not start the web app in live mode alongside this run:
```sh
python -m repair_proof.live_eval --ledger ./meta-live-approved-batch.json --fixtures inclusive-total first-position --max-calls 10 --budget-usd 1.00 --approve-live-spend
```
This runs TWO requests, not ten. To test more, choose the entire approved batch before starting (at most ten distinct registry IDs). Every original attempt counts; automatic retries are **zero**. Do not split/repeat the approved budget across fresh ledger paths. Do not delete/rename a ledger to retry. Any additional batch after this one needs approval that accounts for existing exposure.

**Do not run this command merely to test setup.** Offline checks are `python -m unittest discover -s tests -v`. No keys are needed for tests. The runner does not require `RP_ENABLE_LIVE` because explicit CLI approval is its separate opt-in; leave the web app live switch off.

## Conditional conservative exposure bound
Official Meta Standard prices recorded 2026-10-27: input $1.25/million, output $4.25/million; cached input $0.15/million. References: https://dev.meta.ai/docs/pricing-rate-limits and https://dev.meta.ai/docs/token-counting.

The adapter caps the **entire serialized request** (messages, source, JSON schema and configuration) at 24,000 ASCII/UTF-8 bytes, no tools/search, and sends `max_tokens=2400`. Each request reserves an assumed **32,768 input tokens** plus 2,400 output tokens:

`(32,768 × $1.25 + 2,400 × $4.25) / 1,000,000 = $0.051160`

Ten requests reserve **$0.511600**, below the approved $1.00 with $0.488400 headroom. Reservations are not recycled after cheaper calls. Smaller approved budgets must cover all selected reservations before any request begins.

This is a conservative estimate, **not a proven tokenizer bound or provider billing hard cap**. Assumptions: serialized ASCII bytes conservatively bound content tokens; chat/protocol overhead fits the additional 8,768-token allowance; provider honors the output cap and Standard pricing; no additional unreported billable categories, taxes or external concurrent key use. Fixed overhead is not portable and exact preflight token counting for this Chat Completions route has not been validated. If the user requires an absolute billing guarantee, do not run without a verified provider-enforced spend cap. Prefer a fresh dedicated key and any supported provider budget limit; do not invent that such a limit is configured.

## Durable ledger and stop behavior
Before every network attempt, a single-use ledger durably records a pending attempt and full conservative reservation using atomic replacement, file fsync and directory fsync. An exclusive same-ledger process lock prevents concurrent runs. All existing ledgers (completed, pending, halted or otherwise) are refused, so a crashed process cannot blindly repeat a possibly billed call. Even an error that might be pre-send conservatively consumes the reservation and stops the batch.

Timeout, transport/provider/parse error, missing/invalid usage, or reported token count over the ceiling **halts immediately, no retries**. Check provider usage and reconcile before authorizing any new batch. On disk-write failure stop: the pending reservation remains the authoritative uncertainty signal. A stale lock requires inspecting the previous process/ledger; never automatically remove it.

The ledger stores observed input/output token counts, latency, proposal and independent policy outcome. Source is exclusively the trusted synthetic fixture registry; no arbitrary files, paths, source text, credentials or private conversation are accepted. Error strings do not expose provider response bodies/keys. Model proposals remain untrusted JSON data and are not executed.

`usage_cost_upper_usd` is a subtotal calculated from observed token counts at **uncached** Standard prices, not actual billed dollars (cached input may cost less). `billed_cost_usd` stays null; `usage_complete=false` means unknown exposure remains and the subtotal must not be treated as total cost. Conservative `reserved_usd` is separate. Reasoning output is not subtracted from completion tokens. A successful policy verdict is not evidence of repair correctness; Docker execution and semantic citation review are separate steps.

## Limits
Local batch limits cannot govern concurrent callers, other ledger filenames, direct API use or provider billing changes. Run only one approved batch with one dedicated key. CLI exit status 0 means the selected request/usage workflow completed, **not** that all proposed repairs passed policy or tests. Status 2 means refused or halted; do not auto-retry from shell/CI. The web UI has no aggregate budget ledger, so it is not the authorized path for this bounded evaluation.
