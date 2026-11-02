# Dependency reproducibility — 2026-10-27

## Canonical baseline

`requirements.txt` is the canonical compatibility baseline:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip --isolated install --index-url https://pypi.org/simple --no-cache-dir -r requirements.txt
```

Its direct pins are FastAPI 0.112.0, httpx 0.28.1, Pydantic 2.8.2, and
Uvicorn 0.30.6. Python 3.12 is recommended for a clean reproduction; the
fresh local evidence below is for Python 3.13.2 only because no Python 3.12
interpreter was available on that host.

## Fresh direct-baseline reproduction (Python 3.13.2)

At source revision `6a58372ffbd184faa6e3b610406a4d78f3a33cc7`, a new Python
3.13.2 virtual environment installed the canonical direct pins from
`https://pypi.org/simple` with the command above. It used no global package
mutation, credential, model key, Docker image, or cached-package fallback.
The resolved closure included Pydantic Core 2.20.1, Starlette 0.37.2,
httpcore 1.0.9, and h11 0.16.0.

- `python -m pip check` reported no broken requirements.
- A fresh local Git checkout passed **83** offline tests, the 16-case and
  20-case authored-replay policy evaluations, evaluation-snapshot verification,
  and the 49-entry manifest check. The expanded evaluation remains policy-only:
  it did not execute proposed code or query a model.
- The 12 packet-verifier and 17 app/API-boundary tests also passed in that
  environment.

This is a fresh direct-pin PyPI-install result for Python 3.13.2. It does not
establish Python 3.12 portability or fresh-install portability of the optional
full constraints file.

## Hosted Python 3.12 direct-baseline reproduction

The public GitHub Actions [Test run 20](https://github.com/mangeshraut712/repair-proof/actions/runs/41531358721)
at source revision `ee6fe8a00e5bd87868c6e643ea79bbdb6beec2e0` used a fresh
`ubuntu-latest` runner with `actions/setup-python` set to Python 3.12. Its
offline job installed `requirements.txt` with `--no-cache-dir`, then completed:

- `python -m pip check` with no broken requirements;
- the then-current **84**-test offline suite;
- evaluation-snapshot and manifest verification; and
- JavaScript syntax validation.

This is hosted clean-install evidence for the canonical direct baseline on
Python 3.12. It is separate from the local host, where a Python 3.12
interpreter was unavailable. It does **not** establish that `requirements.lock`
installs cleanly or that every future package index will resolve the same
closure.

### Git checkout versus source archive

Use a Git checkout for the complete validation command. A `git archive`
extraction intentionally fails one manifest-related test because
`verify_manifest.py` checks the tracked file set and requires `.git`. This is
not an application/runtime failure and does not affect offline replay, but an
archive alone cannot satisfy the project's full manifest-validation gate.

## Historical local Python 3.12 constrained-index probe

A fresh probe used the preloaded, digest-pinned Python 3.12 image with only a
conservative candidate constraints file mounted. No source, credential, or
private ledger was mounted. The resolver fetched the candidate metadata through
the historical FastAPI/httpx stack, then that controlled probe's configured
index path rejected
`pydantic==2.8.2` as unavailable. Installation stopped before test execution.

This records that prior controlled probe, not a claim that Pydantic 2.8.2 is
generally unavailable from PyPI. The hosted Python 3.12 direct-baseline result
above supersedes the earlier vague CI reference; neither result reproduces the
optional full-lock installation in this local environment.

The original full lock also contained future-dated transitive pins unavailable
from this index. Therefore this environment does **not** establish a fresh,
portable, full-lock install.

## Optional constraints file

`requirements.lock` records conservative historical constraints for operators
whose trusted index serves them. It is optional and intentionally does not
claim fresh-install portability. Do not replace the direct baseline with a lock
claim until a clean environment installs the full file, passes `pip check`,
and passes the current full suite.

## Scope

These findings concern dependency acquisition in this environment only. They
do not constitute a vulnerability audit, guarantee future package-index
availability, or change the project’s network-disabled sandbox limits.
