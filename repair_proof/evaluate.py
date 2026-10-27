"""Actual offline policy metrics. Never reports replay as model performance."""
import argparse
import json
from .fixtures import FIXTURES
from .patch_policy import sha, validate
from .schemas import Proposal
from .sanitize import evidence

def evaluate(include_holdouts=False):
    rows=[]
    for f in FIXTURES.values():
        if f.holdout and not include_holdouts: continue
        lines=evidence(f.log)
        p=Proposal(diagnosis=f.diagnosis,evidence_ids=[lines[2]['id']],edits=[{'path':'src/solution.py','original_sha256':sha(f.source),'replacement':f.replacement}])
        verdict=validate(f.source,p,{line['id'] for line in lines})
        rows.append({'id':f.id,'category':f.category,'holdout':f.holdout,'accepted':verdict['accepted'],'reasons':verdict['reasons'],'citation_ids_valid':set(p.evidence_ids).issubset({line['id'] for line in lines})})
    repairs=[r for r in rows if r['category']=='repairable']; attacks=[r for r in rows if r['category']=='adversarial']
    return {'mode':'authored_replay_policy_only','include_holdouts':include_holdouts,'cases':len(rows),'repairable_policy_acceptance':{'accepted':sum(r['accepted'] for r in repairs),'total':len(repairs)},'unsafe_rejection':{'rejected':sum(not r['accepted'] for r in attacks),'total':len(attacks)},'citation_reference_validity':{'valid':sum(r['citation_ids_valid'] for r in rows),'total':len(rows)},'semantic_evidence_accuracy':None,'before_fail_after_pass':None,'live_model_quality':None,'live_latency_ms':None,'live_tokens':None,'cost_usd':None,'notes':'No code executed, no live model queried. Valid citation IDs do not establish semantic evidence accuracy. Holdouts are authored, visible in source, not a blinded benchmark.','rows':rows}

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--include-holdouts',action='store_true'); args=parser.parse_args()
    print(json.dumps(evaluate(args.include_holdouts),indent=2))
