from typing import List, Optional

from pydantic import BaseModel, Field


class PolicyParameters(BaseModel):
    capacity_shift_pct: float = Field(..., ge=0.0, le=0.30)
    efficiency_bonus_pct: float = Field(..., ge=0.0, le=0.20)
    max_reassignments: int = Field(..., ge=0, le=3)


class PolicyProposal(BaseModel):
    policy_id: str
    parameters: PolicyParameters
    rationale: Optional[str] = None


class RedTeamOutput(BaseModel):
    risks: List[dict]
    recommendations: List[dict]


class MemoOutput(BaseModel):
    summary: List[str]
    memo: str
