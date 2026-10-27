from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class Edit(Strict):
    path: str = Field(min_length=1, max_length=120)
    original_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    replacement: str = Field(min_length=1, max_length=6000)

class Proposal(Strict):
    diagnosis: str = Field(min_length=1, max_length=1600)
    evidence_ids: list[str] = Field(min_length=1, max_length=12)
    edits: list[Edit] = Field(min_length=1, max_length=1)

class Preview(Strict):
    fixture_id: str = Field(min_length=1,max_length=80)
    mode: Literal['replay','recorded','live']

class Verify(Strict):
    proposal_id: str = Field(pattern=r'^[0-9a-f]{32}$')
