# Live semantic validation — 2026-10-27

## Scope

This record validates the two proposals already stored in the completed bounded
synthetic live ledger. It did not make a provider request, create a credential,
or alter the live ledger.

- Model: `muse-spark-1.3`
- Mode: existing live-ledger semantic validation
- Inputs: the two named, newly authored synthetic fixtures only
- Proposal source: the completed two-attempt bounded live evaluation

## Results

| Fixture | Policy revalidation | Citation IDs | Before | After | Result |
| --- | --- | --- | ---: | ---: | --- |
| `inclusive-total` | accepted | valid | 1 | 0 | verified |
| `first-position` | accepted | valid | 1 | 0 | verified |

Each proposal was parsed as data, rechecked against the independent patch
policy and its fixture's redacted evidence IDs, then evaluated against the
unchanged authored test contract. The required failed-before/passed-after
transition was observed for both fixtures.

## Sandbox provenance

Verification used the preloaded digest-pinned Python image
`sha256:12316debbfb86890f6b2d825820612741ba527ad5a44e3902759141d572bfe8f`
through `repair_proof.verifier`.

- Network disabled (`none`)
- No host mounts or forwarded credentials
- Read-only root, non-root user, dropped capabilities and no-new-privileges
- CPU, memory, PID, tmpfs, output and wall-clock bounds enforced by the verifier
- No image pull and no host execution fallback

## Local v4 validation environment

The direct v4 pins (`FastAPI 0.112.0`, `httpx 0.28.1`, `Pydantic 2.8.2`, and
`Uvicorn 0.30.6`) were exercised in a separate Python 3.13.2 virtual
environment with no broken requirements reported. In that historical v4
direct-baseline run, all 49 tests passed, and
the authored replay-policy evaluation completed.

The full v4 lockfile could not be freshly reproduced from this environment's
currently accessible package index because its future-dated transitive pins
were unavailable. This local evidence therefore validates the direct baseline
and test suite, not a fresh installation of every full-lock transitive pin.

## Limitations

This proves only the named authored synthetic tests failed before and passed
after the proposed replacements. It does not establish general repair
correctness, semantic evidence accuracy outside these fixtures, arbitrary-code
safety, or a provider billing result. Policy acceptance and citation validity
are necessary but not sufficient evidence on their own.
