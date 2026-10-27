# Dependency reproducibility — 2026-10-27

## Canonical baseline

`requirements.txt` is the canonical compatibility baseline:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip --isolated install --index-url https://pypi.org/simple --no-cache-dir -r requirements.txt
```

Its direct pins are FastAPI 0.112.0, httpx 0.28.1, Pydantic 2.8.2, and
Uvicorn 0.30.6. Python 3.12 is recommended for a clean reproduction.

## Local evidence

A separate Python 3.13.2 project virtual environment, without global
mutation, was populated from the available compatible direct-pin dependency
closure. It used the direct versions above plus compatible locally available
transitives. In that environment:

- `python -m pip check` reported no broken requirements.
- Historical v4 direct-baseline validation: `python -m unittest discover -s tests -v` passed **49 tests**.
- `python -m repair_proof.evaluate` completed the 16-case authored replay
  policy evaluation.

This is useful local compatibility evidence. It is not evidence of a fresh
PyPI installation or of Python 3.12 portability.

## Python 3.12 clean-install probe

A fresh probe used the preloaded, digest-pinned Python 3.12 image with only a
conservative candidate constraints file mounted. No source, credential, or
private ledger was mounted. The resolver fetched the candidate metadata through
the historical FastAPI/httpx stack, then the current package index rejected
`pydantic==2.8.2` as unavailable. Installation stopped before test execution.

The original full lock also contained future-dated transitive pins unavailable
from this index. Therefore this environment does **not** establish a fresh,
portable, full-lock install.

## Optional constraints file

`requirements.lock` records conservative historical constraints for operators
whose trusted index serves them. It is optional and intentionally does not
claim fresh-install portability. Do not replace the direct baseline with a lock
claim until a clean environment installs the full file, passes `pip check`,
and passes the historical 49-test suite (the current release has additional recorded-mode tests).

## Scope

These findings concern dependency acquisition in this environment only. They
do not constitute a vulnerability audit, guarantee future package-index
availability, or change the project’s network-disabled sandbox limits.
