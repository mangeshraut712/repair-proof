#!/usr/bin/env python3
"""Verify the tracked offline-evaluation snapshots match the current evaluator.

This is reproducibility evidence for the authored fixture and policy corpus. It
does not measure provider quality, prove artifact authenticity, or execute a
repair.
"""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from repair_proof.evaluate import evaluate

REPORTS=(
    (ROOT/'docs'/'evaluation-development.json',False),
    (ROOT/'docs'/'evaluation-all.json',True),
)
NULL_METRICS=(
    'semantic_evidence_accuracy','before_fail_after_pass','live_model_quality',
    'live_latency_ms','live_tokens','cost_usd',
)

def read_report(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>262144:
        raise ValueError(f'Unsafe evaluation report: {path.name}')
    try:
        report=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as error:
        raise ValueError(f'Unreadable evaluation report: {path.name}') from error
    if not isinstance(report,dict):
        raise ValueError(f'Invalid evaluation report: {path.name}')
    return report

def check_invariants(report,path,include_holdouts):
    if report.get('mode')!='authored_replay_policy_only':
        raise ValueError(f'Unexpected evaluation mode: {path.name}')
    if report.get('include_holdouts') is not include_holdouts:
        raise ValueError(f'Unexpected holdout setting: {path.name}')
    if not isinstance(report.get('rows'),list) or len({row.get('id') for row in report['rows'] if isinstance(row,dict)})!=len(report['rows']):
        raise ValueError(f'Invalid fixture rows: {path.name}')
    for field in NULL_METRICS:
        if field not in report or report[field] is not None:
            raise ValueError(f'Unearned metric in evaluation report: {path.name}')

def verify():
    for path,include_holdouts in REPORTS:
        observed=read_report(path)
        check_invariants(observed,path,include_holdouts)
        expected=evaluate(include_holdouts=include_holdouts)
        if observed!=expected:
            raise ValueError(f'Evaluation report differs from current evaluator: {path.name}')
    return len(REPORTS)

def main():
    try:
        count=verify()
    except (OSError,ValueError) as error:
        print(f'Evaluation verification failed: {error}',file=sys.stderr)
        return 1
    print(f'Verified {count} evaluation reports.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
