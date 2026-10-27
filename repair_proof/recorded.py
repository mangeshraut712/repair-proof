"""Pinned, local prior Meta responses; never inference and never fresh execution."""
import json
from pathlib import Path
from .fixtures import FIXTURES
from .patch_policy import sha, validate
from .sanitize import evidence
from .schemas import Proposal

ARTIFACT=Path(__file__).resolve().parent.parent/'docs'/'RECORDED_LIVE_PROOF.json'
ARTIFACT_SHA256='eeb08ec01ab6c25b4862570f8bea2008369a5ae1248b143d74a683aa5ec8ea82'
RECORDED_FIXTURES=('inclusive-total','first-position')

class RecordedError(Exception):
    pass

def load_records():
    """Read only the pinned project artifact; reject all records on any mismatch.

    The digest detects edits relative to this reviewed source release. It is not
    a provider signature or independent authenticity attestation.
    """
    try:
        if ARTIFACT.is_symlink() or ARTIFACT.resolve()!=ARTIFACT.absolute() or ARTIFACT.stat().st_size>32768:raise ValueError()
        raw=ARTIFACT.read_bytes()
        import hashlib
        if len(raw)>32768 or hashlib.sha256(raw).hexdigest()!=ARTIFACT_SHA256:raise ValueError()
        data=json.loads(raw)
        if data['schema_version']!=1 or data['artifact_type']!='sanitized_recorded_live_proof' or data['fresh_api_call'] is not False:raise ValueError()
        if data['source_execution']['model']!='muse-spark-1.3' or data['recorded_observed_at'] is not None:raise ValueError()
        rows=data['fixtures']
        if [row['fixture_id'] for row in rows]!=list(RECORDED_FIXTURES):raise ValueError()
        result={}
        for row in rows:
            f=FIXTURES[row['fixture_id']]
            record=row['recorded_parsed_proposal']
            if record['availability']!='available':raise ValueError()
            proposal=Proposal.model_validate(record['proposal'])
            canonical=json.dumps(proposal.model_dump(),sort_keys=True,separators=(',',':'))
            if sha(canonical)!=record['canonical_sha256']:raise ValueError()
            if row['input_hashes_sha256']!={'source':sha(f.source),'synthetic_evidence':sha(f.log),'test_contract':sha(f.test_source)}:raise ValueError()
            edit=proposal.edits[0]
            if row['patch_ref']['original_sha256']!=sha(f.source) or row['patch_ref']['replacement_sha256']!=sha(edit.replacement):raise ValueError()
            previous=row['docker_semantic_validation']
            if previous['semantic_input_hashes_sha256']!={'fixture_source':sha(f.source),'replacement':sha(edit.replacement),'test_contract':sha(f.test_source)}:raise ValueError()
            if previous['status']!='verified' or previous['before_exit_code']!=1 or previous['after_exit_code']!=0:raise ValueError()
            policy=validate(f.source,proposal,{line['id'] for line in evidence(f.log)})
            if not policy['accepted']:raise ValueError()
            result[f.id]={'proposal':proposal,'proof':{'model':data['source_execution']['model'],'artifact_sha256':ARTIFACT_SHA256,'proposal_sha256':record['canonical_sha256'],'recorded_observed_at':None,'provider_response_id':'unavailable','raw_provider_response_body':'unavailable','previous_verification':{**previous,'historical':True,'notice':'Historical stored result, not execution in this session.'},'usage_estimate':row['usage_estimate'],'limitations':data['limitations']}}
        return result
    except (OSError,ValueError,KeyError,TypeError,IndexError):
        raise RecordedError('Recorded Meta proof unavailable or integrity validation failed. No API call made.') from None
